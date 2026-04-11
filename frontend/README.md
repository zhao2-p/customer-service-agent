# Frontend

这是当前项目的简单前端页面，使用纯 `HTML + CSS + JavaScript` 实现。

## 启动方式

1. 先启动后端

```powershell
uvicorn backend.app.main:app --reload
```

2. 再启动静态文件服务

```powershell
python -m http.server 5500 -d frontend
```

3. 浏览器访问

```text
http://127.0.0.1:5500
```

默认后端地址是：

```text
http://127.0.0.1:8000
```

可以直接在页面中修改。
