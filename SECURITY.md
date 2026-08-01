# SECURITY

本仓库安全与凭据管理指南

## 1) 重要原则
- 绝不在仓库中提交真实凭据（密码、API Key、私钥、连接字符串等）。
- 使用 `.env.example` 做示例（不包含真实值）。把真实凭据放到 CI secrets / 云 Secret Manager。

## 2) 在本仓库中使用的建议做法
- 生产环境：使用 GitHub Actions repository/organization secrets 或云平台的 Secret Manager（GCP Secret Manager、AWS Secrets Manager、Azure Key Vault 等）。
- 本地开发：从 `.env.example` 复制并建立 `.env`，仅用于本地开发与测试，切勿提交 `.env`。
- 代码审查：在 PR 中注意检查示例或文档是否包含敏感信息。

## 3) 提交前检测（开发者）
- 安装并使用 detect-secrets 与 pre-commit：
  - pip install detect-secrets pre-commit
  - detect-secrets scan > .secrets.baseline
  - 审查 baseline，移除误报后提交 `.secrets.baseline`
  - pre-commit install
  - pre-commit run --all-files

## 4) 泄露响应流程（紧急步骤）
1. 识别被泄露的凭据（服务/账户/环境）。
2. 立即在凭据提供方处撤销或 rotate（生成新 key/密码）。
3. 标注受影响项并通知相关人员与安全负责人。记录事件时间线与影响范围。
4. 评估是否需要清理 Git 历史（git filter-repo / BFG）。**注意**：历史重写会改变 commit SHA，影响 forks/PR，需提前沟通并获得批准。
5. 若选择清理历史，按团队批准的步骤操作并同时 rotate 所有受影响凭据。

## 5) 责任分配
- 代码提交者：负责本地检测与不提交敏感信息。提交前运行 pre-commit。 
- 仓库管理员/运维：负责在发现泄露后 rotate keys 与通知运维与安全团队。 
- 安全联系人：负责组织事件响应、审计与改进方案（请在此处填入具体联系人信息）。

## 6) 联系方式（请补充）
- 安全联系人: security@example.com
- 运维联系人: ops@example.com

---

保留说明：
- 我已在 feature/security/config-secrets-fix 分支准备并提交了 `.pre-commit-config.yaml`、`.secrets.baseline`（占位）等文件。请仓库管理员把下列 workflow 文件放到 `.github/workflows/secret-scan.yml`（我已在 earlier messages 给出完整草稿），以便在 push/PR 时自动运行检测并产出 artifact 报告供审查。

如需我现在运行一次本地/分支级扫描并把结果写入 PR 描述，请回复“请扫描并汇报”，我会立即运行并把发现列出。
