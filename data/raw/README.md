# 原始数据目录 (`data/raw`)

本目录存放竞赛/服创下发的原始 NetCDF，按任务分子目录，名称与 `src/` 中模块对应。

## 目录说明（总览）

| 子目录 | 对应模块 | 内容概要 |
|--------|----------|----------|
| `eddy_detection/` | `src/eddy_detection` | 中尺度涡识别：按时间段合并的 `.nc`（`YYYYMMDD_YYYYMMDD.nc`） |
| `element_forecasting/` | `src/element_forecasting` | 水文要素预测：按日单文件 `YYYYMMDD.nc` |
| `anomaly_detection/` | `src/anomaly_detection` | 风浪异常：按年份 `YYYY/`，风与浪各一个 NetCDF |

下文对三类数据分别给出**文件组织**与**NetCDF 内部结构**（基于抽样文件用 `netCDF4` 读取；在 Windows 上若路径含中文，建议先复制到纯英文临时路径再打开，避免库无法打开文件）。

---

## 1. 中尺度涡识别 `eddy_detection/`

### 文件组织

- 命名：`YYYYMMDD_YYYYMMDD.nc`，表示该文件覆盖的起止日期（同一文件内为**逐日**时间序列）。
- 当前示例文件：`19930101_20021231.nc`、`20030101_20121231.nc`、`20130101_20221231.nc`、`20230101_20231231.nc`、`20240101_20241231.nc` 等；各文件时间长度可能为 365 天（平年）或按文件内 `time` 维实际长度为准。

### NetCDF 结构（以 `20230101_20231231.nc` 为例）

| 维度 | 长度 | 说明 |
|------|------|------|
| `time` | 365 | `units`: `days since 1950-01-01`，逐日（如 2023-01-01～2023-12-31） |
| `latitude` | 160 | `degrees_north`，约 **25.0625°N～44.9375°N** |
| `longitude` | 320 | `degrees_east`，约 **140.0625°E～179.9375°E** |

| 变量 | 维度 | 说明 |
|------|------|------|
| `adt` | `(time, latitude, longitude)` | Absolute dynamic topography，`m`，`sea_surface_height_above_geoid` |
| `ugos` | 同上 | 地转流纬向分量，`m/s` |
| `vgos` | 同上 | 地转流经向分量，`m/s` |

全局属性中常见 `title` 指向 DUACS/卫星高度计融合海表高度等产品（具体以文件内 `title`/`institution` 为准）。

---

## 2. 水文要素预测 `element_forecasting/`

### 文件组织

- 命名：`YYYYMMDD.nc`，**一日一个文件**；目录下为大量按日切分的 NetCDF（体量较大，勿提交 Git）。

### NetCDF 结构（以 `19940101.nc` 为例）

| 维度 | 长度 | 说明 |
|------|------|------|
| `time` | 12 | `units`: **`hours since 2000-01-01`**，单日约 **12 个时次**（约 1 小时间隔，覆盖该日一段连续时段） |
| `lat` | 138 | `degrees_north` |
| `lon` | 125 | `degrees_east` |

| 变量 | 维度 | 说明 |
|------|------|------|
| `sst` | `(time, lat, lon)` | 海温，`degC`，`sea_water_temperature` |
| `sss` | 同上 | 海盐，`psu`，`sea_water_salinity` |
| `ssu` | 同上 | 海流纬向分量，`m/s`，`eastward_sea_water_velocity` |
| `ssv` | 同上 | 海流经向分量，`m/s`，`northward_sea_water_velocity` |

机构等元数据以文件内 `institution` 等全局属性为准（示例中为 Naval Research Laboratory）。

---

## 3. 风浪异常 `anomaly_detection/`

### 文件组织

- 按年分子目录：`2014` … `2025`。
- 每年目录内通常包含：
  - `data_stream-oper_stepType-instant.nc`：地面风场（instant）
  - `data_stream-wave_stepType-instant.nc`：海浪（instant）
- `2014` 目录另含 `201401.zip`（若有需要可本地解压，与 NetCDF 关系以赛题说明为准）。

### NetCDF 结构（以 `2020/` 下文件为例）

两文件 **`valid_time` 维一致**（长度 **248**），时间单位为 **`seconds since 1970-01-01`**，步长约 **3 小时**；抽样对应 **当年 12 月 1 日 00:00 UTC～12 月 31 日 21:00 UTC**（即每年文件为 **12 月** 的 3 小时序列，共 248 个时次）。

#### `data_stream-oper_stepType-instant.nc`（风）

| 维度 | 长度 | 说明 |
|------|------|------|
| `valid_time` | 248 | 时间 |
| `latitude` | 241 | 约 **60°N～0°N** |
| `longitude` | 321 | 约 **100°E～180°E** |

| 变量 | 说明 |
|------|------|
| `u10` | 10 m 风 U 分量，`m s-1`，`(valid_time, latitude, longitude)` |
| `v10` | 10 m 风 V 分量，同上 |

另有 `number`、`expver` 等辅助变量。

#### `data_stream-wave_stepType-instant.nc`（浪）

| 维度 | 长度 | 说明 |
|------|------|------|
| `valid_time` | 248 | 与风文件一致 |
| `latitude` | **121** | 与风网格**不一致**（更粗） |
| `longitude` | **161** | 与风网格**不一致** |

| 变量 | 说明 |
|------|------|
| `swh` | 有效波高（combined wind waves and swell） |
| `mwp` | 平均波周期 |
| `mwd` | 平均波向 |

形状均为 `(valid_time, latitude, longitude)`。

**注意：** 风场为 **241×321**，浪为 **121×161**，联合分析需 **重采样/插值** 或分模态建模。

---

## 已做整理

- 去掉多余一层 `服创数据集/` 包装，任务数据直接放在上述子目录中。
- 删除 `海域要素预测/__MACOSX/` 及其中 `._*` 等 macOS 解压垃圾文件。
- 删除各处的 `.DS_Store`。
- 原「海域要素预测」目录重命名为 `element_forecasting/`（与代码模块一致）。

## 残留目录（若存在）

若仍存在名为 **`服创数据集`** 的文件夹，且其中只剩 `风浪异常识别/2014/201401.zip` 等少量文件，这是迁移时的**重复副本**；完整数据已在 `anomaly_detection/` 下。请在关闭可能占用该 zip 的程序（含资源管理器预览、杀毒扫描）后，**整文件夹删除** `服创数据集/` 即可。
