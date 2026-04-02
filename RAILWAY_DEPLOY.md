# 每日反思智能体部署到 Railway 云平台教程

## 项目信息
- GitHub 仓库：https://github.com/hmumu230-ops/daily-reflection-agent
- 本地路径：C:\Users\29980\Desktop\每日反思智能体
- 启动命令：gunicorn app:app（项目已有 Procfile）
- Python Flask 项目

## 部署步骤

### 第一步：安装 Railway CLI
```cmd
npm install -g @railway/cli
```

### 第二步：登录 Railway
```cmd
railway login
```
- 会弹出浏览器，点击 "Continue with GitHub" 完成登录

### 第三步：创建 Railway 项目并关联 GitHub 仓库
1. 打开 https://railway.app/new
2. 点击 "Deploy from GitHub repo"
3. 选择仓库：daily-reflection-agent
4. 点击 "Deploy Now"

### 第四步：设置环境变量
在 Railway 项目设置中添加以下环境变量：
- QIANWEN_API_KEY=sk-dbfbc3eea22a433789397153756e392c
- SECRET_KEY=myreflect2026

### 第五步：部署
部署完成后在 Railway 控制台点击 "Deploy" 按钮重新部署

### 第六步：生成公网域名
在 Railway 项目中点击 "Generate Domain" 生成访问链接

## 项目文件结构
- requirements.txt：Flask==3.1.3, openai==2.30.0, anthropic==0.86.0, python-dotenv==1.2.2, gunicorn==25.3.0
- Procfile：web: gunicorn app:app
- app.py：Flask 主应用

## 注意事项
- 确保 GitHub 仓库已经提交最新代码
- 环境变量要在 Railway 项目设置中添加
- 部署完成后访问生成的域名即可
