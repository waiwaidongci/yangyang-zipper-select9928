# 旅行箱拉链拉片耐拉测点筛选

洲脊箱包扣件实验室用历史破坏试验筛选稳定、布点时间可控的预检测点。分析员导入整批测量台账，worker 执行 Elastic Net 重采样，实验室复核员对照独立批误差后签核。下游质检班下载入选点位、验证明细和待检试片顺序。业务剧本、参数口径和实验边界见 [BUSINESS.md](BUSINESS.md)。

## 启动

```sh
cp .env.example .env
docker compose build backend
docker compose up -d --no-build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

API 基址为 `http://127.0.0.1:19431/api`，OpenAPI JSON 位于 `/api/openapi.json`。MySQL 8.0 的宿主端口为 `17931`。Compose 启动 FastAPI、Python worker、MySQL 和 Redis 四个服务，数据库、Redis 和报告目录使用具名卷。`docker compose down` 保留具名卷。`.env.example` 提供 `COMPOSE_PROJECT_NAME`、`BACKEND_PORT`、`DB_PORT`、`SEED_DEMO` 和 `JWT_SECRET`。应用读取由 Compose 设置的 `DATABASE_URL`、`REDIS_URL`。演示凭证用于本地。

| 演示账号 | 口令 | 业务权限 |
|---|---|---|
| `analyst@demo.local` | `Demo-2611!` | 查看、导入台账，发起计算，查看未签核结果，下载获批报表 |
| `admin@demo.local` | `Demo-2611!` | 分析员权限，另可签核或驳回及读取审计 |
| `viewer@demo.local` | `Demo-2611!` | 查阅台账、获批运行及正式 CSV |

## CSV 与接口

从项目根目录可直接生成完整的 UTF-8 可导入样例。包含 186 片试片，CSV 首行为固定列名。

```sh
PYTHONPATH=backend python3 -m src.domain.fixtures > /tmp/zipper-pull-test.csv
```

| 模块 | 请求 | 请求体或结果 |
|---|---|---|
| 登录 | `POST /api/auth/login` | `email`、`password`，响应含 `access_token`。受保护接口使用 `Authorization: Bearer <token>` |
| 台账 | `GET /api/spec`、`GET /api/datasets`、`GET /api/datasets/{id}` | 字段及参数契约、数据集列表、分页试片 |
| 导入 | `POST /api/datasets` | JSON 对象含 `name`、`csv`，其中 `csv` 为整个 CSV 文件的文本 |
| 运行 | `POST /api/runs` | `dataset_id`、`label` 和可选 `settings`，提交后返回运行 ID |
| 结果 | `GET /api/runs/{id}` | 查询 `status`，完成后读取 `result`，失败时读取 `error` |
| 复核 | `POST /api/runs/{id}/review` | `decision` 和 `note`，由管理员提交 |
| 导出 | `GET /api/runs/{id}/export/{key}` | 签核通过后按结果表键下载 UTF-8 CSV |
| 审计 | `GET /api/audit` | 管理员查看导入、运行与复核事件 |

## 开发

| 路径 | 工具与职责 |
|---|---|
| `backend/src/domain/` | Python 标准库实现输入校验、种子、Elastic Net、稳定点位和批次误差 |
| `backend/src/routes/`、`services/`、`models/` | FastAPI、SQLAlchemy、JWT 权限、队列和结果持久化 |
| `backend/scripts/`、`migrations/` | 幂等演示数据、数据库引导和 worker 心跳 |
| `../../test-artifacts/yangyang-zipper-select/tests/oracle.py` | 独立近端梯度求解、闭式样本、批次隔离及 CSV 断言 |

本地数值验证使用 Python，无需启动服务。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend python3 ../../test-artifacts/yangyang-zipper-select/tests/oracle.py
```

`backend/src/constants/workflow.py` 定义 `admin/analyst/viewer`、`queued/running/completed/failed` 及 `approved/rejected`，分别用于路由鉴权、worker 状态和签核下载。`backend/src/domain/records.py` 定义 `train/holdout/pending`，用于整批导入校验和计算分区。第三方依赖使用各自的许可证。
