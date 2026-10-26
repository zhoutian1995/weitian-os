# 维天 OS ✦

「维天说」的个人桌面网站，用来展示 AI 内容工作流、Skill 工具、知识库和持续升级中的人生 OS。

🔗 **Live**: [willeai.com](https://willeai.com)

按 2026-10-04 的域名分工，`willeai.com` 承载个人主页，`willeai.cn` 承载杭州纬聆科技有限公司官网。用户明确决定 `.cn` 保留现有个人备案并完成页面切换；备案性质与公司内容不一致的问题记录在 KnowledgeBase，不代表单位性质备案已完成。

## 关于

这是维天说的桌面风格个人网站。

- **主页** — 电脑桌面、工作流领取、Skill 工具箱和个人介绍
- **作品集** — 选题、口播、内容生产与知识沉淀入口
- **维天 OS** — 可缩放、拖拽的个人系统无限画布

## 技术栈

纯前端，零框架。HTML + CSS + Vanilla JS，由服务器 Nginx 提供静态页面。

## 来源

基于 [hiesther.me](https://hiesther.me/) by ESTHER不二进行非商业修改，保留原作者署名和许可信息。

2026-10-25的双人群商业承接改动目前仅保留在本地工作区，尚未部署到个人站。原模板商业授权未核实，不能把用户的业务实施授权等同于权利方商用授权，也不能删除或改写本许可。公司站使用原创页面，本次已单独推进；个人站须先取得适当商业授权或明确批准原创替换范围。当前实际部署与验证证据以KnowledgeBase《双人群承接首批实施与验收-20261025》为准。

## 原创学习入口

`/learn/` 是独立原创的AI/FDE学习实践页，HTML、CSS与JS不引用OS模板界面资源；说明见 `learn/LICENSE.md`。它提供程序员、学生和业务背景三种起步任务，作品证据清单、既有资料链接与本人联系码，不代表新收费课程或就业保证。

本轮部署仅允许新增原创学习路径、必要的本人联系码与Sitemap/LLMS导航，以及匿名事件技术补丁；不把本地尚未核实模板商用授权的首页/OS改动一并发布。上线与否以部署回执及公网回读为准。

匿名事件补丁可通过 `scripts/deploy_geo_events.py --site personal --include-learning --expected-static-manifest <SSD静态基线JSON> --expected-release <当前真实release> --receipt <SSD回执>` 部署；公司站事件配置用 `--site company`，使用实际宝塔Nginx路径。两者都保留原release、校验当前版本并按条件回退，不自动提交Git或改变备案。

## 维护检查

```bash
python3 -B scripts/refresh_geo.py
python3 -B scripts/refresh_geo.py --check
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

文章 HTML 是当前可维护正文。`refresh_geo.py` 从首页作者信息和 Sitemap 更新共享结构化数据、分享标签与面包屑短名，不重新导入知识库正文，也不改写 FAQ、发布时间和文章内容。新增重点文章的来源与相关链接保留在对应 HTML 中。

`--check` 只读检查生成结果是否过期。网站仍由手动版本化 release 部署，GitHub 推送不触发上线。

## License

[CC BY-NC 4.0](./LICENSE.md) — 可以学习与参考，请注明出处，不可商用。
