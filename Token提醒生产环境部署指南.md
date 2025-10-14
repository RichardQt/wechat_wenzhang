# Token提醒生产环境部署指南

## 📋 核心文件清单

### 必需文件
```
d:\mynj\wechat_crawler0919\
├── auto_token_monitor.py          # 主监控脚本
├── notify.py                      # 通知功能模块  
├── email_config.json              # 邮件配置文件（需配置）
└── wechat_cache.json              # 微信Token缓存（自动生成）
```

### 运行时生成文件
```
├── reminder_history.json          # 提醒历史记录
├── auto_token_monitor.log         # 运行日志
└── token_monitor.log              # 通知模块日志
```

## ⚙️ 必需配置文件

### email_config.json
```json
{
  "from_email": "your_email@qq.com",
  "password": "your_app_password", 
  "smtp_server": "smtp.qq.com",
  "smtp_port": 587,
  "to_email": "admin@example.com"
}
```

**配置说明：**
- `from_email`: 发送方邮箱地址
- `password`: 邮箱授权码（非登录密码）
- `smtp_server`: SMTP服务器地址
- `smtp_port`: SMTP端口（通常587或465）
- `to_email`: 接收提醒的邮箱地址

## 🚀 生产环境推荐运行命令

### 标准命令（推荐）
```bash
python auto_token_monitor.py --quiet
```

### 其他可选命令
```bash
# 强制发送提醒（忽略历史记录）
python auto_token_monitor.py --force --quiet

# 自定义日志文件
python auto_token_monitor.py --quiet --log-file /path/to/custom.log
```

## ⏰ 定时任务配置

### Windows 任务计划程序

1. **打开任务计划程序**
   - 运行 `taskschd.msc`

2. **创建基本任务**
   - 任务名称：`Token监控提醒`
   - 描述：`微信公众号Token过期监控`

3. **触发器设置**
   - 频率：`每天`
   - 重复任务：`每 2 小时持续时间 1 天`

4. **操作设置**
   ```
   程序或脚本: python
   添加参数: auto_token_monitor.py --quiet
   起始于: d:\mynj\wechat_crawler0919
   ```

5. **条件设置**
   - ✅ 只有在计算机使用交流电源时才启动任务
   - ✅ 如果任务运行超过 30 分钟，请停止任务

### Linux Cron 配置

```bash
# 编辑crontab
crontab -e

# 每2小时执行一次
0 */2 * * * cd /path/to/wechat_crawler0919 && python auto_token_monitor.py --quiet

# 每4小时执行一次（推荐）
0 */4 * * * cd /path/to/wechat_crawler0919 && python auto_token_monitor.py --quiet
```

## ⚠️ 关键注意事项

### 文件权限
- 确保脚本目录有读写权限
- 日志文件需要写入权限
- JSON配置文件需要读取权限

### 网络环境
- 确保服务器能访问SMTP服务器
- 检查防火墙设置允许SMTP端口通信

### 监控频率建议
- **推荐频率：** 每2-4小时执行一次
- **不建议：** 低于1小时（避免频繁检查）
- **最高频率：** 每小时1次（特殊情况下）

### Token有效期
- 微信Token有效期：**96小时（4天）**
- 提醒时机：剩余时间 ≤ 10小时
- 过期提醒：Token已过期立即提醒

## 🔧 故障排除

### 常见问题

#### 1. 邮件发送失败
```
❌ 错误：Authentication failed
✅ 解决：检查email_config.json中的邮箱授权码
```

#### 2. 无法找到Token信息
```
❌ 错误：缓存文件 wechat_cache.json 不存在
✅ 解决：运行login.py或one_click_login.py获取Token
```

#### 3. 权限问题
```
❌ 错误：Permission denied
✅ 解决：检查文件夹权限，确保可读写
```

#### 4. 重复提醒
```
❌ 现象：同一类型提醒多次发送
✅ 解决：正常现象，系统有防重复机制
```

### 日志检查

#### 查看运行日志
```bash
# 查看最新日志
tail -f auto_token_monitor.log

# 查看错误信息
grep "ERROR" auto_token_monitor.log
```

#### 关键日志标识
- `✅ 检查成功: True` - 检查正常
- `📧 邮件已发送: True` - 提醒发送成功
- `⚠️ 需要提醒: True` - 需要提醒
- `ERROR` - 错误信息，需要处理

### 手动测试

#### 测试Token检查
```bash
# 手动检查（显示详细信息）
python auto_token_monitor.py

# 强制发送提醒（测试邮件）
python auto_token_monitor.py --force
```

#### 测试邮件配置
```bash
# 使用notify.py测试邮件发送
python notify.py --manual
```

## 📊 运行状态判断

### 正常运行标志
- 日志文件正常更新
- 无ERROR级别错误
- 提醒邮件能正常发送和接收

### 异常状态处理
1. **检查配置文件**：验证email_config.json格式
2. **验证Token状态**：确认wechat_cache.json存在且有效
3. **测试网络连接**：确保能连接SMTP服务器
4. **查看详细日志**：分析具体错误原因

## 🎯 快速部署步骤

1. **准备文件**：确保核心文件完整
2. **配置邮箱**：编辑email_config.json
3. **测试运行**：执行 `python auto_token_monitor.py --force`
4. **设置定时任务**：按照系统类型配置定时任务
5. **监控日志**：确认定时任务正常执行

---

**部署完成后**，系统将自动监控Token状态，在Token即将过期或已过期时发送邮件提醒。建议定期检查日志文件确保系统正常运行。