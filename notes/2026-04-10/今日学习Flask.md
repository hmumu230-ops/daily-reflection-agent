# Flask Web 开发学习笔记

## 路由系统
- @app.route() 装饰器定义 URL 和处理函数的映射
- 支持动态路由 /user/<name>
- methods 参数控制 GET/POST

## 模板渲染
- Jinja2 模板引擎
- render_template() 传递变量到 HTML
- 模板继承 {% extends "base.html" %}

## 今日心得
Flask 的设计哲学是"微框架"，核心很小但扩展性强。和 Django 相比更适合小项目快速上手。
