# personal-ip-vault-builder

個人 IP 知識庫建構器。這是一個供 Codex 使用的 Skill，協助新建、檢視或遷移以本人資料為核心的 Markdown Vault。

可以支援 CV、個人網站、Portfolio、內容素材、個人成長與帳號管理。實際分類、Profile 數目、語言及私隱偏好由使用者決定。

## 套件

- [SKILL.md](SKILL.md)：建構、檢視、遷移及交付流程。
- [blueprint.md](references/blueprint.md)：分類邊界、來源／狀態規則和空白模板。
- [validate_vault.py](scripts/validate_vault.py)：唯讀結構與連結檢查，附獨立暫存自測。
- [openai.yaml](agents/openai.yaml)：Codex 顯示名稱及啟動提示。

套件包含通用方法與空白片段；不包含作者的 Vault、履歷、私人紀錄或帳號資料。

## 安裝

把此 repo／套件連結交給 Codex，要求安裝 `personal-ip-vault-builder`。也可將整個 Skill 資料夾放到自己的 Codex skills 目錄；預設為 `~/.codex/skills/personal-ip-vault-builder`，如設定了 CODEX_HOME 則使用其 skills 子目錄。

資料夾內須直接包含 SKILL.md。目的地已有同名 Skill 時，先比較差異再更新。安裝後在新 task 以 `$personal-ip-vault-builder` 使用。

## 使用例子

```text
用 $personal-ip-vault-builder 幫我建立個人 IP Vault，
先支援整理背景及改 CV；內容帳號定位未定。
```

```text
用 $personal-ip-vault-builder 檢視現有 Vault，
找出分類重複、來源追蹤及私隱分層問題，先給我建議。
```

```text
用 $personal-ip-vault-builder 把現有模板遷移成個人 IP Vault，
保留我的資料，列出每項待清理內容及處理方式。
```

## 驗證

需要 Python 3.9 或以上，驗證程式只使用標準函式庫。在 Skill 資料夾執行：

```bash
python3 scripts/validate_vault.py --self-test
python3 scripts/validate_vault.py /absolute/path/to/the-vault
python3 scripts/validate_vault.py /absolute/path/to/the-vault --exclude personal-private --legacy-term OLD_EXAMPLE_NAME
```

預設檢查 AGENTS.md、INDEX.md、VAULT-STATUS.md 和一般 Markdown 行內連結。Wiki／reference links 需另外人工檢查；anchor、外站及內容真實性不在程式檢查範圍。

程式略過已定義私密目錄、private 筆記內文、原始文件、Archive、隱藏檔及 symlink。報告會標示範圍；結構通過不等於資料已核實、沒有敏感內容或獲准發布。

建庫後以使用者提供並允許使用的第一份 source 驗收一次實際用途。尚未提供 source 時，保留「結構可用，實際資料流程待驗收」狀態。
