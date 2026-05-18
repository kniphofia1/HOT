# ADR 0006：本地团队协作边界

## 状态

Accepted

## 背景

终局 Milestone 7 要把个人情报工具升级为小团队情报室，包括用户、团队空间、共享信源、收藏、标注、简报审核和操作日志。
正式账号体系、多租户隔离和计费属于后续 SaaS 阶段，不能在本阶段混做。

## 决策

M7 先实现本地团队协作对象：

- `TeamUser`
- `TeamSpace`
- `TeamMembership`
- `SourceSpaceLink`
- `EventBookmark`
- `EventAnnotation`
- `BriefReview`
- `AuditLog`

所有操作通过显式 `actorUserId` 记录操作者，不实现密码、登录、会话、OAuth 或租户隔离。

## 影响

正面影响：

- 团队协作对象和审计链路可以先被产品验证。
- 每个判断能看到是谁标注、谁审核、谁导出。
- M8 可以在这些对象之上补正式组织、角色权限、数据隔离和计费。

约束：

- 本阶段不是安全登录系统。
- 不把团队空间当作 SaaS 租户边界。
