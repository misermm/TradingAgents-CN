from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class AnalystRegistry:
    _instance = None
    _masters = {}
    _regular = {}
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_master(
        cls,
        master_id: str,
        name_cn: str,
        name_en: str,
        style: str,
        display_name: str,
        create_func,
        philosophy: str = "",
        framework: str = "",
        output_format: str = "",
        max_tool_calls: int = 1,
    ):
        if master_id in cls._masters:
            logger.debug(f"[Registry] 大师 {master_id} 已注册，跳过")
            return
        cls._masters[master_id] = {
            "id": master_id,
            "name_cn": name_cn,
            "name_en": name_en,
            "style": style,
            "display_name": display_name,
            "create_func": create_func,
            "philosophy": philosophy,
            "framework": framework,
            "output_format": output_format,
            "max_tool_calls": max_tool_calls,
            "report_key": f"{master_id}_report",
            "counter_key": f"{master_id}_tool_call_count",
        }
        logger.debug(f"[Registry] 注册大师: {name_cn}({master_id})")

    @classmethod
    def register_regular(cls, analyst_id: str, display_name: str, create_func, max_tool_calls: int = 3):
        cls._regular[analyst_id] = {
            "id": analyst_id,
            "display_name": display_name,
            "create_func": create_func,
            "max_tool_calls": max_tool_calls,
            "report_key": f"{analyst_id}_report",
            "counter_key": f"{analyst_id}_tool_call_count" if analyst_id != "social" else "sentiment_tool_call_count",
        }

    @classmethod
    def get_master(cls, master_id: str) -> dict:
        return cls._masters.get(master_id)

    @classmethod
    def get_all_masters(cls) -> dict:
        return dict(cls._masters)

    @classmethod
    def get_master_ids(cls) -> list:
        return list(cls._masters.keys())

    @classmethod
    def get_master_display_name(cls, master_id: str) -> str:
        info = cls._masters.get(master_id)
        return info["display_name"] if info else master_id.replace("_", " ").title()

    @classmethod
    def get_report_keys(cls) -> list:
        return [m["report_key"] for m in cls._masters.values()]

    @classmethod
    def get_counter_keys(cls) -> list:
        return [m["counter_key"] for m in cls._masters.values()]

    @classmethod
    def build_initial_state_fields(cls) -> dict:
        fields = {
            "master_reports": {m["id"]: "" for m in cls._masters.values()},
            "master_tool_call_counts": {m["id"]: 0 for m in cls._masters.values()},
        }
        return fields

    @classmethod
    def build_master_report_filter_keywords(cls) -> list:
        return [m["id"] for m in cls._masters.values()] + ["master_consensus"]

    @classmethod
    def ensure_initialized(cls):
        if not cls._initialized:
            cls._initialized = True
            cls._do_auto_register()

    @classmethod
    def _do_auto_register(cls):
        try:
            from tradingagents.agents.masters import (
                MASTER_ANALYST_IDS,
                MASTER_ANALYST_INFO,
                MASTER_CREATE_FUNCS,
            )

            DISPLAY_NAMES = {
                "warren_buffett": "Warren Buffett",
                "peter_lynch": "Peter Lynch",
                "ben_graham": "Ben Graham",
                "charlie_munger": "Charlie Munger",
                "cathie_wood": "Cathie Wood",
                "bill_ackman": "Bill Ackman",
                "phil_fisher": "Phil Fisher",
                "stanley_druckenmiller": "Druckenmiller",
                "aswath_damodaran": "Aswath Damodaran",
                "michael_burry": "Michael Burry",
                "mohnish_pabrai": "Mohnish Pabrai",
                "nassim_taleb": "Nassim Taleb",
                "rakesh_jhunjhunwala": "Rakesh Jhunjhunwala",
            }

            for master_id in MASTER_ANALYST_IDS:
                info = MASTER_ANALYST_INFO.get(master_id, {})
                AnalystRegistry.register_master(
                    master_id=master_id,
                    name_cn=info.get("name_cn", master_id),
                    name_en=info.get("name_en", master_id),
                    style=info.get("style", ""),
                    display_name=DISPLAY_NAMES.get(master_id, master_id.replace("_", " ").title()),
                    create_func=MASTER_CREATE_FUNCS.get(master_id),
                )
        except ImportError as e:
            logger.warning(f"[Registry] 延迟注册大师失败(非致命): {e}")

    @classmethod
    def clear(cls):
        cls._masters = {}
        cls._regular = {}
        cls._initialized = False
