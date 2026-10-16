# 数据与维护

GitHub Actions 每 6 小时采集、测试、提交数据并部署 Pages，也可在 Actions 手动运行。任务可能延迟；公共仓库长期无活动可能被停用计划任务。网页刷新按钮仅重新读取已发布结果，不查询物业后台。静态 GitHub Pages 不提供秒级库存保证。

## 自动来源

| 来源 | 获取内容 | 范围 |
| --- | --- | --- |
| ACC / The Block | 已跟踪的 2026 学年 1B1B 户型及全部档位的价格、状态 | 非 The Block 全部户型或租期 |
| Bridge at Northwest Hills | 官网全部户型、价格范围、公开日期 | 户型而非获批房号 |
| Urban Choice / AppFolio | 公开招租列表的地址、房号、租金、日期 | 仅地图研究片区，不抓详情页 |
| Westside Group / AppFolio | 同上 | 同上 |

注册表在 `data/sources.json`。其他物业官网与平台记录保留人工核查。UT Off-Campus、Zillow、Apartments.com 仅为外部查询入口，不计作接入库存。Google 评分独立人工核查，不随租金采集更新时间。

采集遵循 robots 路径及 Crawl-delay；不登录、不绕过挑战和 403。失败保留旧资料并显示错误，不修改该来源成功观察时间。完整成功响应中未出现的旧记录标记 unavailable，默认隐藏；记录骤降超过70%拒绝覆盖，需人工核对。未出现可能因下架、研究范围或标识变化，不能自动断言已出租。

`lastAttemptAt` 是尝试时间；`lastSuccessAt` 和 `observedAt` 是成功观察时间；`checkedAt` 是该记录核查日；`ratingCheckedAt` 单独用于评分。`provenance` 保留价格、状态、日期的原链接及观察时间。NOW 表示来源当时称可租，不代表保留至计划日期；重复 NOW 不改动首次观察到的可租日。

后续价格、状态和日期变化保存在 `data/changes.json`，最多300条，不代表完整历史。记录分具体 unit 与 floorplan 档位，不可把记录数当独立空房数。楼盘归类不把不同计价方式合并成统一价格。

## 地图来源

- [APD CrimeViewer](https://maps.austintexas.gov/arcgis/rest/services/CrimeViewer_new/APD_Reported_Crimes_new/FeatureServer)：近90天，层0–8，按RIN去重后除研究面积，以本页三分位分组；暴力子集 homicide、robbery、aggravated assault。只发布聚合统计。
- [UT Shuttle](https://parking.utexas.edu/transportation/shuttles)：研究片区参考匹配，非站点距离或时间验证。
- [City of Austin Street Centerline](https://services.arcgis.com/0L95CJ0VTaxqcmED/ArcGIS/rest/services/TRANSPORTATION_street_segment/FeatureServer/0)：本地备用道路图；[OpenStreetMap](https://www.openstreetmap.org/copyright)：在线瓦片。Leaflet许可证在vendor目录。

研究范围为自定义矩形，可能重叠，不是官方社区边界。APD统计不含UTPD单独日志、Part II或未报案事件，未按人口、人流调整；低密度不代表安全。无收录房源不代表无空房。

## 本地开发

无需安装运行依赖，Python标准库与Node.js即可。在仓库根目录：

```sh
python -m http.server 8766 --bind 127.0.0.1
python scripts/collect.py
python scripts/refresh_crime.py --as-of YYYY-MM-DD
python scripts/refresh_roads.py
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/model.test.mjs
```

访问 http://127.0.0.1:8766 。不能双击HTML读取本地JSON。公开发布仅index.html、assets、data。新增适配器先核对公开路径、价格口径、地理范围及稳定标识，补充解析失败和部分失败测试；不要仅凭HTTP200修改核查日期。人工记录只有实际核查后才能更新日期。收藏保存在访客本机，无申请材料上传功能。
