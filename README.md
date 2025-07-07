### Discord 機器人 README
這是一個使用 Python 和 Discord.py 框架開發的多功能 Discord 機器人，包含多個 Cog 模組，提供直播通知、遊戲、等級系統、投票、歡迎訊息、YouTube 通知、管理功能等功能。以下是使用範例與說明，適合在 Windows 環境下開發。

### 免責聲明
本 Discord 機器人專案（以下簡稱「本專案」）由開發者提供，僅供個人學習和非商業用途使用。使用本專案即表示你同意以下條款：

1. **API 和金鑰**：本專案需要使用第三方 API（如 YouTube API、Twitch API、Reddit API 等），相關 API 金鑰和 Secret Key 需由使用者自行申請並配置在 `.env` 文件中。開發者不提供任何 API 金鑰，對於因使用者未正確配置或違反 API 使用條款導致的問題概不負責。
2. **第三方內容**：本專案可能通過 API 獲取第三方內容（如迷因圖片、天氣數據），這些內容的版權屬於原作者或提供者。使用者需自行遵守相關版權法規，並在分發或使用時標註來源。開發者對第三方內容的合法性不承擔任何責任。
3. **使用風險**：本專案為開源軟件，按「原樣」提供。開發者不保證其穩定性、安全性或適用性，對於因使用本專案導致的任何損失（包括但不限於數據丟失、服務中斷或法律糾紛），概不負責。
4. **修改與分發**：使用者可以根據所選許可證（例如 MIT 許可證）修改和分發本專案，但需保留原始版權聲明並遵守依賴庫的許可條件。

如有疑問，請聯繫開發者或參考相關 API 的官方文件。使用本專案即表示你接受上述免責條款。

**最後更新時間：2025年7月7日晚上8:44 CST**

### 必要條件
- Python 3.8+
- 安裝依賴：
  ```bash
  pip install discord.py aiohttp matplotlib numpy sqlite3 python-dotenv google-api-python-client
  ```
- 環境變數設定（使用 `.env` 文件）：
  - `DISCORD_TOKEN`：Discord Bot Token
  - `WEATHER_API_KEY`：WeatherAPI API Key（已修復，但金鑰需一段時間啟用）
  - `YT_API_KEY`：YouTube API Key
  - `REDDIT_CLIENT_ID`：Reddit API Client ID
  - `REDDIT_CLIENT_SECRET`：Reddit API Client Secret

### 安裝與運行
1. 將程式碼克隆到本地：
   ```bash
   git clone <你的倉庫URL>
   cd <專案目錄>
   ```
2. 創建 `bot_data.db` 資料庫文件，放置在專案目錄下。
3. 創建 `.env` 文件並填入上述環境變數。
4. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```
5. 運行機器人：
   ```bash
   python main.py
   ```
   （假設主程式為 `main.py`，並正確載入所有 Cog）

### 使用範例
機器人提供多個模組的指令，需根據權限使用。以下是各模組的指令範例：

#### General Cog
- **測試延遲**:
  ```
  !ping
  ```
  - 回應：`Ping! 延遲：XXms`
- **查看幫助**:
  ```
  !myhelp
  ```
  - 顯示所有模組的指令列表。
- **使用者資訊**:
  ```
  !userinfo @User
  ```
  - 顯示指定用戶的加入時間、身份組等資訊（預設為自己）。
- **伺服器資訊**:
  ```
  !serverinfo
  ```
  - 顯示伺服器名稱、擁有者、成員數等。

#### Game Cog
- **開始猜數字遊戲**:
  ```
  !game start
  ```
  - 回應：`✅ 遊戲開始！請猜一個 1-100 之間的數字，你有 5 次機會。`
- **猜測數字**:
  ```
  !game guess 50
  ```
  - 根據數字提示結果（太大/太小/正確）。
- **結束遊戲**:
  ```
  !game end
  ```
  - 回應：`✅ 遊戲結束，數字是 XX。`
- **查看排行榜**:
  ```
  !game leaderboard
  ```
  - 顯示猜數字遊戲得分前 10 名。
- **獲取迷因**:
  ```
  !meme reddit
  ```
  - 從 Reddit 獲取迷因圖片（可選 `memeapi`）。

#### Level Cog
- **查看等級**:
  ```
  !level
  ```
  - 顯示自己的等級、經驗值進度等。
- **查看排行榜**:
  ```
  !leaderboard
  ```
  - 顯示等級排行榜（分頁顯示）。
- **設定等級系統**（需管理權限）:
  ```
  !levelconfig channel #level-up
  ```
  - 設定升級通知頻道。

#### Vote Cog
- **創建投票**（Slash Command）:
  ```
  /createpoll "你喜歡哪種飲料?" 咖啡|茶|水
  ```
  - 創建投票並顯示按鈕。
- **查看投票結果**:
  ```
  /pollresult <poll_id>
  ```
  - 顯示投票結果圖表。
- **列出活躍投票**:
  ```
  /listpolls
  ```
  - 列出所有活躍投票。
- **傳統投票命令**:
  ```
  !poll "你喜歡哪種飲料?" 咖啡|茶|水
  ```
  - 創建傳統格式投票。

#### WeatherCog
- **注意事項**: WeatherAPI 已修復，但金鑰需一段時間啟用。待金鑰生效後，可使用以下指令查看天氣。
- **查詢天氣**:
  ```
  !getweather Taipei
  ```
  - 顯示台北的當前天氣資訊（包括溫度、狀況等，待金鑰啟用後生效）。
- **設定天氣頻道**（需管理權限）:
  ```
  !setweatherchannel #weather Taipei,Tokyo
  ```
  - 設定天氣通知頻道和城市（逗號分隔），待金鑰啟用後生效。

#### ModerationCog
- **創建身份組**:
  ```
  !addrole Moderator
  ```
  - 創建名為 `Moderator` 的身份組。
- **分配身份組**:
  ```
  !assignrole @User Moderator
  ```
  - 為指定用戶分配 `Moderator` 身份組。
- **刪除訊息**:
  ```
  !clear 10
  ```
  - 刪除最近 10 條訊息。

#### Welcome Cog
- **設定歡迎頻道**:
  ```
  !welcome channel #welcome
  ```
  - 設定歡迎訊息發送頻道。
- **設定自動角色**:
  ```
  !welcome role @Member
  ```
  - 為新成員自動分配 `Member` 角色。
- **測試歡迎訊息**:
  ```
  !welcome test
  ```
  - 在指定頻道發送測試歡迎訊息。

#### YTNotificationCog
- **設定 YouTube 通知**:
  ```
  !setytchannels #youtube UC123 UC456
  ```
  - 設定通知頻道並追蹤 YouTube 頻道 ID。
- **列出追蹤頻道**:
  ```
  !listytchannels
  ```
  - 顯示目前追蹤的 YouTube 頻道。

#### Twitch Cog
- **查看系統狀態**:
  ```
  !twitch
  ```
  - 顯示系統狀態、API 狀態、通知頻道等。
- **設定 API 金鑰**:
  ```
  !twitch setkey <Client_ID> <Client_Secret>
  ```
  - 在私人頻道設定 Twitch API 金鑰。
- **添加實況主**:
  ```
  !twitch add streamer123 @StreamerRole
  ```
  - 添加實況主並指定提及角色。
- **測試通知**:
  ```
  !twitch test streamer123
  ```
  - 測試對指定實況主的通知。

### 注意事項
- **權限要求**: 部分指令需管理員權限，請確保機器人有足夠的 Discord 權限。
- **資料庫路徑**: 確保 `bot_data.db` 位於專案目錄下。
- **WeatherAPI 狀態**: WeatherAPI 已修復，但金鑰尚未啟用，相關功能暫時待機。

### 部署與測試
- **本地測試**: 運行 `python main.py`，在 Discord 伺服器中測試指令。
- **遠端部署**: 上傳至伺服器（如 AWS EC2），同步 `bot_data.db`，並監控日誌。
- **問題回饋**: 若指令無效，請檢查日誌並提供錯誤訊息。

### 貢獻與回饋
如有問題或建議，請提供日誌輸出或錯誤訊息，我們會盡快協助。你也可以提交 Pull Request 參與開發！

---

### Discord Bot README
This is a multifunctional Discord bot developed using Python and the Discord.py framework, featuring various Cog modules for live notifications, games, leveling systems, voting, welcome messages, YouTube notifications, moderation, and more. It is designed to be developed in a Windows environment. Below are usage examples and instructions.

### Disclaimer
This Discord bot project (hereinafter referred to as "the Project") is provided by the developer for personal learning and non-commercial use only. By using the Project, you agree to the following terms:

1. **API and Keys**: The Project requires the use of third-party APIs (e.g., YouTube API, Twitch API, Reddit API), and the corresponding API keys and Secret Keys must be obtained and configured by the user in the `.env` file. The developer does not provide any API keys and is not responsible for issues arising from improper configuration or violation of API usage terms by the user.
2. **Third-Party Content**: The Project may retrieve third-party content (e.g., meme images, weather data) via APIs. The copyright of such content belongs to the original authors or providers. Users must comply with relevant copyright laws and credit the source when distributing or using the content. The developer assumes no responsibility for the legality of third-party content.
3. **Usage Risks**: This Project is open-source software provided "as is." The developer does not guarantee its stability, security, or suitability for any purpose. The developer is not liable for any losses (including but not limited to data loss, service interruptions, or legal disputes) resulting from the use of this Project.
4. **Modification and Distribution**: Users may modify and distribute the Project according to the chosen license (e.g., MIT License), provided they retain the original copyright notice and comply with the license terms of dependent libraries.

For any questions, please contact the developer or refer to the official documentation of the relevant APIs. Using this Project indicates your acceptance of the above disclaimer.

**Last updated: 8:44 PM CST, July 07, 2025**

### Prerequisites
- Python 3.8+
- Install dependencies:
  ```bash
  pip install discord.py aiohttp matplotlib numpy sqlite3 python-dotenv google-api-python-client
  ```
- Environment variable setup (using a `.env` file):
  - `DISCORD_TOKEN`: Discord Bot Token
  - `WEATHER_API_KEY`: WeatherAPI API Key (repaired, but activation pending)
  - `YT_API_KEY`: YouTube API Key
  - `REDDIT_CLIENT_ID`: Reddit API Client ID
  - `REDDIT_CLIENT_SECRET`: Reddit API Client Secret

### Installation and Running
1. Clone the code to your local machine:
   ```bash
   git clone <your repository URL>
   cd <project directory>
   ```
2. Create a `bot_data.db` database file in the project directory.
3. Create a `.env` file and fill in the environment variables listed above.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the bot:
   ```bash
   python main.py
   ```
   (Assuming the main program is `main.py` and all Cogs are loaded correctly)

### Usage Examples
The bot provides commands across multiple modules, with some requiring specific permissions. Below are examples for each module:

#### General Cog
- **Test Latency**:
  ```
  !ping
  ```
  - Response: `Ping! Latency: XXms`
- **View Help**:
  ```
  !myhelp
  ```
  - Displays a list of commands for all modules.
- **User Information**:
  ```
  !userinfo @User
  ```
  - Shows details like join date and roles for the specified user (defaults to self).
- **Server Information**:
  ```
  !serverinfo
  ```
  - Displays server name, owner, member count, etc.

#### Game Cog
- **Start Number Guessing Game**:
  ```
  !game start
  ```
  - Response: `✅ Game started! Guess a number between 1-100, you have 5 attempts.`
- **Guess a Number**:
  ```
  !game guess 50
  ```
  - Provides feedback (too high/too low/correct).
- **End Game**:
  ```
  !game end
  ```
  - Response: `✅ Game ended, the number was XX.`
- **View Leaderboard**:
  ```
  !game leaderboard
  ```
  - Shows the top 10 scores for the guessing game.
- **Get a Meme**:
  ```
  !meme reddit
  ```
  - Fetches a meme from Reddit (optional `memeapi` source).

#### Level Cog
- **Check Level**:
  ```
  !level
  ```
  - Displays your level, XP progress, etc.
- **View Leaderboard**:
  ```
  !leaderboard
  ```
  - Shows the level leaderboard (paginated).
- **Configure Level System** (Requires Manage Guild Permission):
  ```
  !levelconfig channel #level-up
  ```
  - Sets the channel for level-up notifications.

#### Vote Cog
- **Create a Poll** (Slash Command):
  ```
  /createpoll "Which drink do you like?" coffee|tea|water
  ```
  - Creates a poll with interactive buttons.
- **View Poll Results**:
  ```
  /pollresult <poll_id>
  ```
  - Displays a chart of poll results.
- **List Active Polls**:
  ```
  /listpolls
  ```
  - Lists all active polls.
- **Traditional Poll Command**:
  ```
  !poll "Which drink do you like?" coffee|tea|water
  ```
  - Creates a poll in traditional command format.

#### WeatherCog
- **Note**: WeatherAPI has been repaired, but the API key is pending activation and will take some time to become fully operational. Once activated, the following commands will be available.
- **Check Weather**:
  ```
  !getweather Taipei
  ```
  - Displays the current weather information for Taipei (including temperature, conditions, etc., available after key activation).
- **Set Weather Channel** (Requires Manage Guild Permission):
  ```
  !setweatherchannel #weather Taipei,Tokyo
  ```
  - Sets the weather notification channel and cities (comma-separated), functional after key activation.

#### ModerationCog
- **Create Role**:
  ```
  !addrole Moderator
  ```
  - Creates a role named `Moderator`.
- **Assign Role**:
  ```
  !assignrole @User Moderator
  ```
  - Assigns the `Moderator` role to the specified user.
- **Clear Messages**:
  ```
  !clear 10
  ```
  - Deletes the last 10 messages.

#### Welcome Cog
- **Set Welcome Channel**:
  ```
  !welcome channel #welcome
  ```
  - Sets the channel for welcome messages.
- **Set Auto Role**:
  ```
  !welcome role @Member
  ```
  - Automatically assigns the `Member` role to new members.
- **Test Welcome Message**:
  ```
  !welcome test
  ```
  - Sends a test welcome message to the designated channel.

#### YTNotificationCog
- **Set YouTube Notification**:
  ```
  !setytchannels #youtube UC123 UC456
  ```
  - Sets the notification channel and tracks YouTube channel IDs.
- **List Tracked Channels**:
  ```
  !listytchannels
  ```
  - Displays currently tracked YouTube channels.

#### Twitch Cog
- **View System Status**:
  ```
  !twitch
  ```
  - Shows system status, API status, notification channel, etc.
- **Set API Key**:
  ```
  !twitch setkey <Client_ID> <Client_Secret>
  ```
  - Sets Twitch API keys (run in a private channel to avoid exposing keys).
- **Add Streamer**:
  ```
  !twitch add streamer123 @StreamerRole
  ```
  - Adds a streamer and specifies a mention role.
- **Test Notification**:
  ```
  !twitch test streamer123
  ```
  - Tests a notification for the specified streamer.

### Important Notes
- **Permission Requirements**: Some commands require admin permissions; ensure the bot has sufficient Discord permissions.
- **Database Path**: Ensure `bot_data.db` is in the project directory.
- **WeatherAPI Status**: WeatherAPI is repaired, but the key is pending activation, so weather features are temporarily unavailable.

### Deployment and Testing
- **Local Testing**: Run `python main.py` and test commands in your Discord server.
- **Remote Deployment**: Upload to a server (e.g., AWS EC2), sync `bot_data.db`, and monitor logs.
- **Feedback**: If a command fails, check the logs and provide error messages for assistance.

### Contribution and Feedback
If you encounter issues or have suggestions, please provide log outputs or error messages, and we’ll assist you promptly. Feel free to submit Pull Requests to contribute to the development!

---
