# Token提醒自动化功能说明

## 功能概述

本次更新为微信公众号Token过期提醒系统添加了完整的自动化检测和防重复提醒机制，确保Token状态监控的可靠性和高效性。

## 🆕 新增功能

### 1. 防重复提醒机制
- **智能提醒历史记录**：系统会记录每次提醒的时间和类型
- **避免重复发送**：同一类型的提醒只会发送一次，直到Token更新
- **自动重置机制**：当检测到新Token时，会自动重置提醒历史

### 2. 自动化检测功能
- **自动检测函数**：[`auto_check_and_notify()`](notify.py:159)新增智能检测功能
- **Token变化监控**：自动检测Token更新，并重置提醒状态
- **详细日志记录**：完整记录所有检测和提醒活动

### 3. 独立监控脚本
- **专用监控脚本**：[`auto_token_monitor.py`](auto_token_monitor.py)可独立运行
- **适合定时任务**：专为系统定时任务优化设计
- **多种运行模式**：支持自动、强制、静默等模式

## 📁 文件结构说明

### 核心文件

| 文件名 | 功能说明 |
|--------|----------|
| [`notify.py`](notify.py) | 主要的通知模块，包含所有核心功能 |
| [`auto_token_monitor.py`](auto_token_monitor.py) | 独立的自动监控脚本，适合定时任务 |
| [`reminder_history.json`](reminder_history.json) | 提醒历史记录文件（自动生成） |

### 日志文件

| 文件名 | 功能说明 |
|--------|----------|
| `token_monitor.log` | notify.py的运行日志 |
| `auto_token_monitor.log` | 自动监控脚本的专用日志 |

### 配置文件

| 文件名 | 功能说明 |
|--------|----------|
| [`email_config.json`](email_config.json) | 邮件发送配置 |
| [`wechat_cache.json`](wechat_cache.json) | 微信Token缓存文件 |

## 🚀 使用方法

### notify.py 使用方式

#### 1. 传统手动模式（向后兼容）
```bash
# 基本用法（默认手动模式）
python notify.py

# 显式指定手动模式
python notify.py --manual
```

#### 2. 新增自动模式
```bash
# 自动模式（推荐用于定时任务）
python notify.py --auto

# 自动静默模式
python notify.py --auto --quiet
```

#### 3. 命令行参数说明
```bash
python notify.py --help
```

| 参数 | 说明 |
|------|------|
| `--auto` | 自动模式：使用防重复提醒机制 |
| `--manual` | 手动模式：忽略提醒历史，强制发送（默认） |
| `--quiet` | 静默模式：只输出关键信息 |

### auto_token_monitor.py 使用方式

#### 1. 基本自动监控
```bash
# 标准自动监控
python auto_token_monitor.py

# 静默模式（推荐用于定时任务）
python auto_token_monitor.py --quiet
```

#### 2. 强制模式
```bash
# 强制发送提醒（忽略历史记录）
python auto_token_monitor.py --force

# 静默强制模式
python auto_token_monitor.py --force --quiet
```

#### 3. 自定义日志文件
```bash
# 指定自定义日志文件
python auto_token_monitor.py --log-file custom_monitor.log
```

## 🔧 提醒历史数据结构

[`reminder_history.json`](reminder_history.json)文件结构如下：

```json
{
  "current_token_hash": "7b3ad64ce6119d808f94716890f53811",
  "last_pre_expiry_reminder": null,
  "last_expired_reminder": "2025-10-13T12:34:54.360469",
  "reminder_count": {
    "pre_expiry": 0,
    "expired": 1
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `current_token_hash` | String | 当前Token的MD5哈希值 |
| `last_pre_expiry_reminder` | String/null | 最后一次预过期提醒的时间 |
| `last_expired_reminder` | String/null | 最后一次过期提醒的时间 |
| `reminder_count` | Object | 各类型提醒的发送次数统计 |

## ⏰ 定时任务配置

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（建议每2-4小时）
4. 操作设置：
   ```
   程序: python
   参数: d:\mynj\wechat_crawler0919\auto_token_monitor.py --quiet
   起始位置: d:\mynj\wechat_crawler0919
   ```

### Linux Cron

添加到crontab：
```bash
# 每2小时检查一次
0 */2 * * * cd /path/to/project && python auto_token_monitor.py --quiet

# 每4小时检查一次
0 */4 * * * cd /path/to/project && python auto_token_monitor.py --quiet
```

## 🔍 提醒逻辑说明

### 提醒时机

| 状态 | 提醒类型 | 触发条件 |
|------|----------|----------|
| 即将过期 | `pre_expiry` | 剩余时间 ≤ 10小时 |
| 已过期 | `expired` | 剩余时间 ≤ 0小时 |

### 防重复机制

1. **Token不变情况**：同一Token的相同类型提醒只发送一次
2. **Token更新情况**：检测到新Token时自动重置提醒历史
3. **历史记录持久化**：提醒历史保存在JSON文件中

## 📊 日志监控

### 日志级别

- **INFO**：正常运行信息
- **WARNING**：警告信息
- **ERROR**：错误信息

### 重要日志示例

```
2025-10-13 12:34:54,532 - INFO - 开始自动检测token状态...
2025-10-13 12:34:54,532 - INFO - expired类型的提醒已经发送过，跳过
2025-10-13 12:34:54,534 - INFO - expired类型的提醒已发送过，跳过重复提醒
```

## 🛠️ 故障排除

### 常见问题

#### 1. Unicode编码错误
**症状**：运行时出现`UnicodeEncodeError`
**解决方案**：已修复，使用文本标签替代表情符号

#### 2. 提醒历史文件权限问题
**症状**：无法创建或写入`reminder_history.json`
**解决方案**：
```bash
# 检查目录权限
ls -la reminder_history.json

# 修复权限（Linux/macOS）
chmod 664 reminder_history.json
```

#### 3. 邮件配置问题
**症状**：提醒邮件发送失败
**解决方案**：检查[`email_config.json`](email_config.json)配置是否正确

### 调试模式

启用详细日志输出：
```bash
# 使用手动模式查看详细信息
python notify.py --manual

# 查看日志文件
tail -f token_monitor.log
```

## 🔄 向后兼容性

### 保证兼容性

✅ **现有调用方式完全兼容**
```bash
python notify.py  # 仍然按照原有逻辑工作
```

✅ **所有原有功能正常工作**
- [`check_token_expiry()`](notify.py:282)函数
- [`send_token_expiry_notification()`](notify.py:334)函数
- [`send_email_notification()`](notify.py:238)函数

✅ **配置文件格式不变**
- [`email_config.json`](email_config.json)格式保持不变
- [`wechat_cache.json`](wechat_cache.json)格式保持不变

## 📚 函数文档

### 新增核心函数

#### [`get_current_token_hash()`](notify.py:22)
获取当前token的MD5哈希值，用于检测token变化。

#### [`load_reminder_history()`](notify.py:51)
加载提醒历史记录，如果文件不存在则创建默认记录。

#### [`save_reminder_history(history)`](notify.py:85)
保存提醒历史记录到JSON文件。

#### [`should_send_reminder(reminder_type, history, current_token_hash)`](notify.py:104)
判断是否应该发送提醒，核心的防重复逻辑。

#### [`record_reminder_sent(reminder_type, history)`](notify.py:139)
记录提醒已发送，更新历史记录。

#### [`auto_check_and_notify()`](notify.py:159)
自动检测token状态并发送提醒的主要函数。

## ✅ 推荐配置

### 生产环境推荐

1. **使用自动监控脚本**
   ```bash
   python auto_token_monitor.py --quiet
   ```

2. **配置定时任务**
   - 频率：每2-4小时检查一次
   - 使用静默模式减少系统负载

3. **日志管理**
   - 定期清理日志文件
   - 监控日志文件大小

### 开发/测试环境

1. **使用详细输出模式**
   ```bash
   python notify.py --auto
   ```

2. **查看实时日志**
   ```bash
   tail -f token_monitor.log
   ```

---

## 📝 更新记录

**版本**：2024.10.13
**更新内容**：
- ✅ 添加完整的防重复提醒机制
- ✅ 实现自动化检测功能
- ✅ 创建独立的监控脚本
- ✅ 添加详细的日志记录
- ✅ 保证完全向后兼容
- ✅ 修复Unicode编码问题

**作者**：Kilo Code  
**创建时间**：2024年10月13日