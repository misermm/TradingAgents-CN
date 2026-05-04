MASTER_ANALYST_IDS = [
    "warren_buffett",
    "peter_lynch",
    "ben_graham",
    "charlie_munger",
    "cathie_wood",
    "bill_ackman",
    "phil_fisher",
    "stanley_druckenmiller",
    "aswath_damodaran",
    "michael_burry",
    "mohnish_pabrai",
    "nassim_taleb",
    "rakesh_jhunjhunwala",
]

MASTER_ANALYST_INFO = {
    "warren_buffett": {"name_cn": "巴菲特", "name_en": "Warren Buffett", "style": "价值投资"},
    "peter_lynch": {"name_cn": "彼得·林奇", "name_en": "Peter Lynch", "style": "成长投资"},
    "ben_graham": {"name_cn": "格雷厄姆", "name_en": "Ben Graham", "style": "价值投资之父"},
    "charlie_munger": {"name_cn": "芒格", "name_en": "Charlie Munger", "style": "理性投资"},
    "cathie_wood": {"name_cn": "凯瑟琳·伍德", "name_en": "Cathie Wood", "style": "颠覆式创新"},
    "bill_ackman": {"name_cn": "阿克曼", "name_en": "Bill Ackman", "style": "激进投资"},
    "phil_fisher": {"name_cn": "费舍尔", "name_en": "Phil Fisher", "style": "长期成长"},
    "stanley_druckenmiller": {"name_cn": "德鲁肯米勒", "name_en": "Stanley Druckenmiller", "style": "宏观交易"},
    "aswath_damodaran": {"name_cn": "达莫达兰", "name_en": "Aswath Damodaran", "style": "估值院长"},
    "michael_burry": {"name_cn": "布瑞", "name_en": "Michael Burry", "style": "逆向投资"},
    "mohnish_pabrai": {"name_cn": "帕伯莱", "name_en": "Mohnish Pabrai", "style": "丹霍低风险"},
    "nassim_taleb": {"name_cn": "塔勒布", "name_en": "Nassim Taleb", "style": "黑天鹅风险"},
    "rakesh_jhunjhunwala": {"name_cn": "朱朱瓦拉", "name_en": "Rakesh Jhunjhunwala", "style": "新兴市场成长"},
}

_MASTER_IMPORT_MAP = {
    "warren_buffett": ("tradingagents.agents.masters.warren_buffett", "create_warren_buffett_analyst"),
    "peter_lynch": ("tradingagents.agents.masters.peter_lynch", "create_peter_lynch_analyst"),
    "ben_graham": ("tradingagents.agents.masters.ben_graham", "create_ben_graham_analyst"),
    "charlie_munger": ("tradingagents.agents.masters.charlie_munger", "create_charlie_munger_analyst"),
    "cathie_wood": ("tradingagents.agents.masters.cathie_wood", "create_cathie_wood_analyst"),
    "bill_ackman": ("tradingagents.agents.masters.bill_ackman", "create_bill_ackman_analyst"),
    "phil_fisher": ("tradingagents.agents.masters.phil_fisher", "create_phil_fisher_analyst"),
    "stanley_druckenmiller": ("tradingagents.agents.masters.stanley_druckenmiller", "create_stanley_druckenmiller_analyst"),
    "aswath_damodaran": ("tradingagents.agents.masters.aswath_damodaran", "create_aswath_damodaran_analyst"),
    "michael_burry": ("tradingagents.agents.masters.michael_burry", "create_michael_burry_analyst"),
    "mohnish_pabrai": ("tradingagents.agents.masters.mohnish_pabrai", "create_mohnish_pabrai_analyst"),
    "nassim_taleb": ("tradingagents.agents.masters.nassim_taleb", "create_nassim_taleb_analyst"),
    "rakesh_jhunjhunwala": ("tradingagents.agents.masters.rakesh_jhunjhunwala", "create_rakesh_jhunjhunwala_analyst"),
}

_MASTER_CREATE_CACHE = {}


def _get_create_func(master_id: str):
    if master_id in _MASTER_CREATE_CACHE:
        return _MASTER_CREATE_CACHE[master_id]
    if master_id not in _MASTER_IMPORT_MAP:
        return None
    module_path, func_name = _MASTER_IMPORT_MAP[master_id]
    import importlib
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    _MASTER_CREATE_CACHE[master_id] = func
    return func


@property
def _MASTER_CREATE_FUNCS(cls):
    result = {}
    for mid in MASTER_ANALYST_IDS:
        func = _get_create_func(mid)
        if func:
            result[mid] = func
    return result


class _MasterCreateFuncsAccessor:
    def __getitem__(self, key):
        func = _get_create_func(key)
        if func is None:
            raise KeyError(key)
        return func

    def __contains__(self, key):
        return key in _MASTER_IMPORT_MAP

    def get(self, key, default=None):
        func = _get_create_func(key)
        return func if func is not None else default

    def keys(self):
        return _MASTER_IMPORT_MAP.keys()

    def items(self):
        for mid in _MASTER_IMPORT_MAP:
            func = _get_create_func(mid)
            if func:
                yield mid, func

    def values(self):
        for mid in _MASTER_IMPORT_MAP:
            func = _get_create_func(mid)
            if func:
                yield func

    def __iter__(self):
        return iter(_MASTER_IMPORT_MAP)

    def __len__(self):
        return len(_MASTER_IMPORT_MAP)


MASTER_CREATE_FUNCS = _MasterCreateFuncsAccessor()


def __getattr__(name):
    _LAZY_EXPORTS = {
        "create_warren_buffett_analyst": ("tradingagents.agents.masters.warren_buffett", "create_warren_buffett_analyst"),
        "create_peter_lynch_analyst": ("tradingagents.agents.masters.peter_lynch", "create_peter_lynch_analyst"),
        "create_ben_graham_analyst": ("tradingagents.agents.masters.ben_graham", "create_ben_graham_analyst"),
        "create_charlie_munger_analyst": ("tradingagents.agents.masters.charlie_munger", "create_charlie_munger_analyst"),
        "create_cathie_wood_analyst": ("tradingagents.agents.masters.cathie_wood", "create_cathie_wood_analyst"),
        "create_bill_ackman_analyst": ("tradingagents.agents.masters.bill_ackman", "create_bill_ackman_analyst"),
        "create_phil_fisher_analyst": ("tradingagents.agents.masters.phil_fisher", "create_phil_fisher_analyst"),
        "create_stanley_druckenmiller_analyst": ("tradingagents.agents.masters.stanley_druckenmiller", "create_stanley_druckenmiller_analyst"),
        "create_aswath_damodaran_analyst": ("tradingagents.agents.masters.aswath_damodaran", "create_aswath_damodaran_analyst"),
        "create_michael_burry_analyst": ("tradingagents.agents.masters.michael_burry", "create_michael_burry_analyst"),
        "create_mohnish_pabrai_analyst": ("tradingagents.agents.masters.mohnish_pabrai", "create_mohnish_pabrai_analyst"),
        "create_nassim_taleb_analyst": ("tradingagents.agents.masters.nassim_taleb", "create_nassim_taleb_analyst"),
        "create_rakesh_jhunjhunwala_analyst": ("tradingagents.agents.masters.rakesh_jhunjhunwala", "create_rakesh_jhunjhunwala_analyst"),
    }
    if name in _LAZY_EXPORTS:
        import importlib
        module_path, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_warren_buffett_analyst",
    "create_peter_lynch_analyst",
    "create_ben_graham_analyst",
    "create_charlie_munger_analyst",
    "create_cathie_wood_analyst",
    "create_bill_ackman_analyst",
    "create_phil_fisher_analyst",
    "create_stanley_druckenmiller_analyst",
    "create_aswath_damodaran_analyst",
    "create_michael_burry_analyst",
    "create_mohnish_pabrai_analyst",
    "create_nassim_taleb_analyst",
    "create_rakesh_jhunjhunwala_analyst",
    "MASTER_ANALYST_IDS",
    "MASTER_ANALYST_INFO",
    "MASTER_CREATE_FUNCS",
]
