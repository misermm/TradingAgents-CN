"""
用户服务 - 基于数据库的用户管理
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from bson import ObjectId

from app.core.config import settings
from app.models.user import User, UserCreate, UserUpdate, UserResponse

try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

logger = get_logger('user_service')


class UserService:
    """用户服务类"""

    _FALLBACK_USERS = {
        "admin": {
            "username": "admin",
            "email": "admin@tradingagents.cn",
            "hashed_password": hashlib.sha256("admin123".encode()).hexdigest(),
            "is_active": True,
            "is_verified": True,
            "is_admin": True,
            "preferences": {
                "default_market": "A股",
                "default_depth": "深度",
                "ui_theme": "light",
                "language": "zh-CN",
            },
            "daily_quota": 10000,
            "concurrent_limit": 10,
        }
    }

    def __init__(self):
        self._db_available = False
        self._last_db_check = 0.0
        self._db_check_interval = 30.0
        self._refresh_db_connection()

    def _refresh_db_connection(self) -> bool:
        now = time.monotonic()
        if self._db_available and (now - self._last_db_check) < self._db_check_interval:
            return True
        try:
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            db.command('ping')
            self._users_collection = db.users
            self._db_available = True
            self._last_db_check = now
            return True
        except Exception as e:
            if self._db_available:
                logger.warning(f"UserService MongoDB 连接丢失，将使用回退认证: {e}")
            self._db_available = False
            self._last_db_check = now
            return False

    @property
    def users_collection(self):
        if self._db_available:
            try:
                from app.core.database import get_mongo_db_sync
                db = get_mongo_db_sync()
                return db.users
            except Exception:
                self._refresh_db_connection()
                if self._db_available:
                    return self._users_collection
        return None

    def close(self):
        pass

    def __del__(self):
        self.close()

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return UserService.hash_password(plain_password) == hashed_password

    def _get_users_collection(self):
        self._refresh_db_connection()
        if self._db_available:
            try:
                from app.core.database import get_mongo_db_sync
                db = get_mongo_db_sync()
                return db.users
            except Exception:
                pass
        return None

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        try:
            coll = self._get_users_collection()
            if coll is None:
                logger.warning("数据库不可用，无法创建用户")
                return None

            existing_user = coll.find_one({"username": user_data.username})
            if existing_user:
                logger.warning(f"用户名已存在: {user_data.username}")
                return None

            existing_email = coll.find_one({"email": user_data.email})
            if existing_email:
                logger.warning(f"邮箱已存在: {user_data.email}")
                return None

            user_doc = {
                "username": user_data.username,
                "email": user_data.email,
                "hashed_password": self.hash_password(user_data.password),
                "is_active": True,
                "is_verified": False,
                "is_admin": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_login": None,
                "preferences": {
                    "default_market": "A股",
                    "default_depth": "3",
                    "default_analysts": ["市场分析师", "基本面分析师"],
                    "auto_refresh": True,
                    "refresh_interval": 30,
                    "ui_theme": "light",
                    "sidebar_width": 240,
                    "language": "zh-CN",
                    "notifications_enabled": True,
                    "email_notifications": False,
                    "desktop_notifications": True,
                    "analysis_complete_notification": True,
                    "system_maintenance_notification": True
                },
                "daily_quota": 1000,
                "concurrent_limit": 3,
                "total_analyses": 0,
                "successful_analyses": 0,
                "failed_analyses": 0,
                "favorite_stocks": []
            }

            result = coll.insert_one(user_doc)
            user_doc["_id"] = result.inserted_id

            logger.info(f"✅ 用户创建成功: {user_data.username}")
            return User(**user_doc)

        except Exception as e:
            logger.error(f"❌ 创建用户失败: {e}")
            return None

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        try:
            logger.info(f"[authenticate_user] 开始认证用户: {username}")

            coll = self._get_users_collection()
            if coll is None:
                fallback = self._FALLBACK_USERS.get(username)
                if fallback and self.verify_password(password, fallback["hashed_password"]):
                    logger.info(f"[authenticate_user] 内存回退认证成功: {username}")
                    return User(**fallback)
                logger.warning(f"[authenticate_user] 内存回退认证失败: {username}")
                return None

            user_doc = coll.find_one({"username": username})
            logger.info(f"[authenticate_user] 数据库查询结果: {'找到用户' if user_doc else '用户不存在'}")

            if not user_doc:
                fallback = self._FALLBACK_USERS.get(username)
                if fallback and self.verify_password(password, fallback["hashed_password"]):
                    logger.info(f"[authenticate_user] 回退认证成功: {username}")
                    return User(**fallback)
                logger.warning(f"[authenticate_user] 用户不存在: {username}")
                return None

            if not self.verify_password(password, user_doc["hashed_password"]):
                logger.warning(f"[authenticate_user] 密码错误: {username}")
                return None

            if not user_doc.get("is_active", True):
                logger.warning(f"[authenticate_user] 用户已禁用: {username}")
                return None

            coll.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )

            logger.info(f"[authenticate_user] 用户认证成功: {username}")
            return User(**user_doc)

        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            fallback = self._FALLBACK_USERS.get(username)
            if fallback and self.verify_password(password, fallback["hashed_password"]):
                logger.info(f"[authenticate_user] 异常回退认证成功: {username}")
                return User(**fallback)
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        try:
            coll = self._get_users_collection()
            if coll is None:
                fallback = self._FALLBACK_USERS.get(username)
                return User(**fallback) if fallback else None
            user_doc = coll.find_one({"username": username})
            if user_doc:
                return User(**user_doc)
            fallback = self._FALLBACK_USERS.get(username)
            return User(**fallback) if fallback else None
        except Exception as e:
            logger.error(f"❌ 获取用户失败: {e}")
            fallback = self._FALLBACK_USERS.get(username)
            return User(**fallback) if fallback else None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            coll = self._get_users_collection()
            if coll is None:
                for fallback in self._FALLBACK_USERS.values():
                    if fallback.get("username") == user_id:
                        return User(**fallback)
                return None
            if not ObjectId.is_valid(user_id):
                return None

            user_doc = coll.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                return User(**user_doc)
            for fallback in self._FALLBACK_USERS.values():
                if fallback.get("username") == user_id:
                    return User(**fallback)
            return None
        except Exception as e:
            logger.error(f"❌ 获取用户失败: {e}")
            return None

    async def update_user(self, username: str, user_data: UserUpdate) -> Optional[User]:
        try:
            coll = self._get_users_collection()
            if coll is None:
                logger.warning("数据库不可用，无法更新用户")
                return None

            update_data = {"updated_at": datetime.now(timezone.utc)}

            if user_data.email:
                existing_email = coll.find_one({
                    "email": user_data.email,
                    "username": {"$ne": username}
                })
                if existing_email:
                    logger.warning(f"邮箱已被使用: {user_data.email}")
                    return None
                update_data["email"] = user_data.email

            if user_data.preferences:
                update_data["preferences"] = user_data.preferences.model_dump()

            if user_data.daily_quota is not None:
                update_data["daily_quota"] = user_data.daily_quota

            if user_data.concurrent_limit is not None:
                update_data["concurrent_limit"] = user_data.concurrent_limit

            result = coll.update_one(
                {"username": username},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.info(f"✅ 用户信息更新成功: {username}")
                return await self.get_user_by_username(username)
            else:
                logger.warning(f"用户不存在或无需更新: {username}")
                return None

        except Exception as e:
            logger.error(f"❌ 更新用户信息失败: {e}")
            return None

    async def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        try:
            user = await self.authenticate_user(username, old_password)
            if not user:
                logger.warning(f"旧密码验证失败: {username}")
                return False

            coll = self._get_users_collection()
            if coll is None:
                return False

            new_hashed_password = self.hash_password(new_password)
            result = coll.update_one(
                {"username": username},
                {
                    "$set": {
                        "hashed_password": new_hashed_password,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"✅ 密码修改成功: {username}")
                return True
            else:
                logger.error(f"❌ 密码修改失败: {username}")
                return False

        except Exception as e:
            logger.error(f"❌ 修改密码失败: {e}")
            return False

    async def reset_password(self, username: str, new_password: str) -> bool:
        try:
            coll = self._get_users_collection()
            if coll is None:
                return False

            new_hashed_password = self.hash_password(new_password)
            result = coll.update_one(
                {"username": username},
                {
                    "$set": {
                        "hashed_password": new_hashed_password,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"✅ 密码重置成功: {username}")
                return True
            else:
                logger.error(f"❌ 密码重置失败: {username}")
                return False

        except Exception as e:
            logger.error(f"❌ 重置密码失败: {e}")
            return False

    async def create_admin_user(self, username: str = "admin", password: str = "admin123", email: str = "admin@tradingagents.cn") -> Optional[User]:
        try:
            coll = self._get_users_collection()
            if coll is None:
                logger.warning("数据库不可用，无法创建管理员")
                return None

            existing_admin = coll.find_one({"username": username})
            if existing_admin:
                logger.info(f"管理员用户已存在: {username}")
                return User(**existing_admin)

            admin_doc = {
                "username": username,
                "email": email,
                "hashed_password": self.hash_password(password),
                "is_active": True,
                "is_verified": True,
                "is_admin": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_login": None,
                "preferences": {
                    "default_market": "A股",
                    "default_depth": "深度",
                    "ui_theme": "light",
                    "language": "zh-CN",
                    "notifications_enabled": True,
                    "email_notifications": False
                },
                "daily_quota": 10000,
                "concurrent_limit": 10,
                "total_analyses": 0,
                "successful_analyses": 0,
                "failed_analyses": 0,
                "favorite_stocks": []
            }

            result = coll.insert_one(admin_doc)
            admin_doc["_id"] = result.inserted_id

            logger.info(f"✅ 管理员用户创建成功: {username}")
            logger.info(f"   密码: {password}")
            logger.info("   ⚠️  请立即修改默认密码！")

            return User(**admin_doc)

        except Exception as e:
            logger.error(f"❌ 创建管理员用户失败: {e}")
            return None

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        try:
            coll = self._get_users_collection()
            if coll is None:
                return []

            cursor = coll.find().skip(skip).limit(limit)
            users = []

            for user_doc in cursor:
                user = User(**user_doc)
                users.append(UserResponse(
                    id=str(user.id),
                    username=user.username,
                    email=user.email,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at,
                    last_login=user.last_login,
                    preferences=user.preferences,
                    daily_quota=user.daily_quota,
                    concurrent_limit=user.concurrent_limit,
                    total_analyses=user.total_analyses,
                    successful_analyses=user.successful_analyses,
                    failed_analyses=user.failed_analyses
                ))

            return users

        except Exception as e:
            logger.error(f"❌ 获取用户列表失败: {e}")
            return []

    async def deactivate_user(self, username: str) -> bool:
        try:
            coll = self._get_users_collection()
            if coll is None:
                return False

            result = coll.update_one(
                {"username": username},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"✅ 用户已禁用: {username}")
                return True
            else:
                logger.warning(f"用户不存在: {username}")
                return False

        except Exception as e:
            logger.error(f"❌ 禁用用户失败: {e}")
            return False

    async def activate_user(self, username: str) -> bool:
        try:
            coll = self._get_users_collection()
            if coll is None:
                return False

            result = coll.update_one(
                {"username": username},
                {
                    "$set": {
                        "is_active": True,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count > 0:
                logger.info(f"✅ 用户已激活: {username}")
                return True
            else:
                logger.warning(f"用户不存在: {username}")
                return False

        except Exception as e:
            logger.error(f"❌ 激活用户失败: {e}")
            return False


user_service = UserService()
