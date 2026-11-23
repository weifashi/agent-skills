-- 自有统计的事件表（SQLite / D1 写法，换数据库时改类型即可）。
-- 不存：IP、浏览器型号原文、邮箱、地址栏参数、表单里的自由文本、金额。
-- visitor_id 只在访客同意后才有；view_id 是一次打开页面（只在内存里，不写进用户设备）。
-- account_id 只在后端核对过「这个请求确实是这个账号的」之后才写。
CREATE TABLE growth_events (
  id TEXT PRIMARY KEY,              -- 客户端生成的事件编号，用来去重
  received_at INTEGER NOT NULL,     -- 服务端收到的时间（毫秒）
  occurred_at INTEGER NOT NULL,     -- 客户端发生的时间（毫秒），服务端校验过范围
  app TEXT NOT NULL CHECK(app IN ('site','admin','app')),   -- 哪一端；按项目改
  event TEXT NOT NULL,              -- 事件名，服务端有按端的白名单
  view_id TEXT NOT NULL,
  visitor_id TEXT,
  account_id TEXT,
  path TEXT NOT NULL,               -- 页面路径，不带参数
  page_code TEXT,                   -- 页面编号（落地页版本等）
  lang TEXT,
  device TEXT CHECK(device IS NULL OR device IN ('mobile','tablet','desktop')),
  referrer TEXT,                    -- 从哪个网站来，只记域名
  source TEXT, medium TEXT, campaign TEXT, term TEXT, content TEXT,   -- utm 各项
  lp TEXT,                          -- 落地页编号
  ref TEXT,                         -- 合作伙伴编号
  props_json TEXT NOT NULL CHECK(json_valid(props_json) AND json_type(props_json)='object')
);
CREATE INDEX growth_events_time ON growth_events(occurred_at);
CREATE INDEX growth_events_event_time ON growth_events(event, occurred_at);
CREATE INDEX growth_events_visitor ON growth_events(visitor_id, occurred_at) WHERE visitor_id IS NOT NULL;
CREATE INDEX growth_events_account ON growth_events(account_id, occurred_at) WHERE account_id IS NOT NULL;
CREATE INDEX growth_events_view ON growth_events(view_id);

-- 同意过的访客注册以后，把访客编号和账号对应起来：他注册前在官网的访问也归到这个账号名下。
CREATE TABLE growth_visitor_account (
  visitor_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  linked_at INTEGER NOT NULL
);

-- 推广花费：在内部后台按渠道、按时间段录入，「按来源」报表用它算每个客户的成本。
CREATE TABLE growth_ad_spend (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  campaign TEXT,
  day_from TEXT NOT NULL,           -- YYYY-MM-DD
  day_to TEXT NOT NULL,
  amount_minor INTEGER NOT NULL,    -- 最小货币单位
  currency TEXT NOT NULL,
  note TEXT
);
