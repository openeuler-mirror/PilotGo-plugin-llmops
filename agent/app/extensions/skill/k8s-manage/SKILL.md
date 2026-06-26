---
name: k8s-manage
description: 面向多集群 Kubernetes 日常运维与交付的一体化技能，覆盖环境安装初始化（k8s-installer）、基础集群管理（k8s-cluster-manager）、应用部署发布（k8s-deployer）、批量作业与一次性任务（k8s-job-runner）。适用于从零安装 kubelet/kubeadm 到多 kube context 场景下的巡检、准入与变更控制、灰度/回滚、紧急处置、跨集群一致性与批量操作。支持 Linux 与 Windows 双平台。
---

# K8s Manage（安装、多集群运维与交付）

本技能将四类高频角色能力整合在一起，覆盖多集群实战中约 80% 的常见操作场景：

- **k8s-installer（环境安装）**：Linux/Windows 平台 kubelet/kubeadm/kubectl 安装、节点加入集群、KUBECONFIG 配置
- **k8s-cluster-manager（基础管理）**：多集群选择、巡检、容量与节点、命名空间与配额、RBAC 与安全、证据化排障、变更控制
- **k8s-deployer（应用部署）**：声明式交付、Helm/Kustomize、滚动更新/灰度、配置变更、扩缩容、发布失败诊断与回滚
- **k8s-job-runner（批量作业）**：Job/CronJob、批量触发与追踪、并发控制、失败重试、数据/脚本一次性任务的安全执行

> 默认假设你可以使用 `kubectl`，并且通过 kubeconfig（或 `KUBECONFIG` 环境变量）管理多个 context（多集群）。

## KUBECONFIG 环境变量使用说明

`KUBECONFIG` 环境变量用于指定 kubectl 读取的 kubeconfig 文件路径（支持多个文件以冒号/分号分隔）。这是跨平台（Linux/macOS/Windows）通用的配置方式：

### Linux/macOS

```bash
# 查看当前配置
export KUBECONFIG=/path/to/config

# 合并多个 kubeconfig 文件
export KUBECONFIG="~/.kube/config:~/.kube/another-config"

# 验证配置生效
kubectl config get-contexts
kubectl config current-context
```

### Windows (PowerShell)

```powershell
# 设置 KUBECONFIG 环境变量
$env:KUBECONFIG="C:\Users\YourName\.kube\config"

# 查看当前配置
kubectl config view

# 验证配置生效
kubectl config get-contexts
```

### Windows (CMD)

```cmd
set KUBECONFIG=C:\Users\YourName\.kube\config
kubectl config get-contexts
```

> **注意**：设置 `KUBECONFIG` 后，kubectl 会优先使用此环境变量指定的配置文件，而非默认的 `~/.kube/config`。

## 全局原则（多集群必守）

### 1) 先定范围，再执行

每次操作必须先明确：
- **context**（目标集群）
- **namespace**
- **资源范围**（名称 / labelSelector / kind 列表）
- **变更级别**（只读巡检 / 可回滚变更 / 高风险破坏性操作）

### 2) 先读后写 + 证据链

任何写操作前，先收集现状证据（至少满足其一）：
- `kubectl get ... -o wide|yaml`
- `kubectl describe ...`（含 Events）
- `kubectl get events ... --sort-by=.lastTimestamp`

并在输出里保留：关键字段、风险点、回滚路径。

### 3) 变更必须可回滚

- Deployment/StatefulSet：优先使用 `rollout undo` 或回退镜像 tag/values
- Helm：优先使用 `helm rollback`（若使用 Helm）
- 配置：保留变更前的 YAML（或明确能从 Git/Chart 复原）

### 4) 多集群安全护栏

- 禁止在未确认 context 时执行写操作
- 默认避免 `--force`、`--grace-period=0`、`delete pvc/pv` 等破坏性操作；必须执行时要显式警告并给出影响面与替代方案
- 生产环境优先使用最小权限 ServiceAccount（至少提示 RBAC 风险）

## 输出格式（统一）

输出使用以下结构，便于审计与复盘：

```text
🎯 目标与范围
- context: <ctx>
- namespace: <ns>
- 资源: <kind/name 或 selector>
- 操作类型: 只读/变更/高风险

🔎 现状证据
- 证据1: <关键输出摘要>
- 证据2: <关键输出摘要>

🧠 判断与方案
- 方案A（推荐）: <做什么/为什么>
- 方案B（备选）: <做什么/代价>

🛠️ 执行步骤
1) ...
2) ...

✅ 验证方法
- ...

↩️ 回滚方案
- ...

⚠️ 风险与注意事项
- ...
```

---

# k8s-installer（环境安装与初始化）

## 典型触发场景

- "如何在 Linux/Windows 上安装 kubelet"
- "如何配置 kubectl 连接远程集群"
- "如何将新节点加入现有集群"
- "如何设置 KUBECONFIG 环境变量"
- "kubelet 服务无法启动如何排查"

## Linux 平台安装 kubelet/kubeadm/kubectl

### 方法一：使用官方源安装（推荐）

**Ubuntu/Debian:**

```bash
# 更新 apt 并安装依赖
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

# 添加 Kubernetes 官方仓库
mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# 安装 kubelet kubeadm kubectl
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

# 启动 kubelet
sudo systemctl enable --now kubelet
```

**CentOS/RHEL/Rocky Linux:**

```bash
# 添加 Kubernetes 官方仓库
sudo cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/repodata/repomd.xml.key
EOF

# 安装 kubelet kubeadm kubectl
sudo yum install -y kubelet kubeadm kubectl

# 启动 kubelet
sudo systemctl enable --now kubelet
```

### 方法二：二进制文件安装

```bash
# 下载指定版本（以 v1.29.0 为例）
VERSION="v1.29.0"
cd /tmp
curl -LO "https://dl.k8s.io/release/${VERSION}/bin/linux/amd64/kubelet"
curl -LO "https://dl.k8s.io/release/${VERSION}/bin/linux/amd64/kubeadm"
curl -LO "https://dl.k8s.io/release/${VERSION}/bin/linux/amd64/kubectl"

# 验证校验和（可选但推荐）
curl -LO "https://dl.k8s.io/release/${VERSION}/bin/linux/amd64/kubelet.sha256"
echo "$(cat kubelet.sha256)  kubelet" | sha256sum --check

# 安装到系统目录
sudo install -o root -g root -m 0755 kubelet kubeadm kubectl /usr/local/bin/

# 创建 systemd 服务文件
sudo cat <<EOF | sudo tee /etc/systemd/system/kubelet.service
[Unit]
Description=kubelet: The Kubernetes Node Agent
Documentation=https://kubernetes.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/local/bin/kubelet
Restart=always
StartLimitInterval=0
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now kubelet
```

### Linux 加入集群

```bash
# 1. 在 Master 节点生成 join token
kubeadm token create --print-join-command

# 2. 在 Worker 节点执行 join 命令（从上面获取）
sudo kubeadm join <control-plane-endpoint>:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash>

# 3. 配置 kubectl（复制 admin.conf 到本地）
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# 或使用 KUBECONFIG 环境变量
export KUBECONFIG=/etc/kubernetes/admin.conf
```

## Windows 平台安装 kubelet

### 准备工作

```powershell
# 创建 Kubernetes 目录
mkdir C:\k
mkdir C:\etc\kubernetes
mkdir C:\var\lib\kubelet
mkdir C:\var\log\kubelet
```

### 下载并安装 kubelet

```powershell
# 下载 kubelet 二进制文件（以 v1.29.0 为例）
$version = "v1.29.0"
$kubeletUrl = "https://dl.k8s.io/release/$version/bin/windows/amd64/kubelet.exe"
$kubeadmUrl = "https://dl.k8s.io/release/$version/bin/windows/amd64/kubeadm.exe"
$kubectlUrl = "https://dl.k8s.io/release/$version/bin/windows/amd64/kubectl.exe"

# 下载到 C:\k 目录
Invoke-WebRequest -Uri $kubeletUrl -OutFile C:\k\kubelet.exe
Invoke-WebRequest -Uri $kubeadmUrl -OutFile C:\k\kubeadm.exe
Invoke-WebRequest -Uri $kubectlUrl -OutFile C:\k\kubectl.exe

# 添加到系统 PATH
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\k", [EnvironmentVariableTarget]::Machine)
```

### 配置 kubelet 服务（Windows Service）

```powershell
# 下载 nssm（Non-Sucking Service Manager）用于创建 Windows 服务
$nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
Invoke-WebRequest -Uri $nssmUrl -OutFile C:\k\nssm.zip
Expand-Archive C:\k\nssm.zip -DestinationPath C:\k\

# 创建 kubelet 服务
C:\k\nssm-2.24\win64\nssm.exe install kubelet "C:\k\kubelet.exe"

# 设置服务参数
C:\k\nssm-2.24\win64\nssm.exe set kubelet AppParameters "--kubeconfig=C:\k\config --pod-infra-container-image=mcr.microsoft.com/oss/kubernetes/pause:3.9 --cgroups-per-qos=false --enforce-node-allocatable= --network-plugin=cni --cni-bin-dir=C:\opt\cni\bin --cni-conf-dir=C:\etc\cni\net.d"
C:\k\nssm-2.24\win64\nssm.exe set kubelet AppDirectory "C:\k"

# 启动服务
Start-Service kubelet
```

### Windows 加入集群

```powershell
# 1. 在 Master 节点生成 join token
kubeadm token create --print-join-command

# 2. 在 Windows 节点执行 join 命令
C:\k\kubeadm.exe join <control-plane-endpoint>:6443 --token <token> `
    --discovery-token-ca-cert-hash sha256:<hash>

# 3. 配置 kubectl
# 从 Master 节点复制 admin.conf 到 Windows 节点 C:\Users\YourName\.kube\config
# 或使用 KUBECONFIG 环境变量
[Environment]::SetEnvironmentVariable("KUBECONFIG", "C:\Users\YourName\.kube\config", [EnvironmentVariableTarget]::User)
```

## kubectl 配置与验证

### 配置 kubeconfig

```bash
# Linux/macOS
export KUBECONFIG=/path/to/your/kubeconfig
kubectl cluster-info

# Windows PowerShell
$env:KUBECONFIG="C:\path\to\your\kubeconfig"
kubectl cluster-info
```

### 验证安装

```bash
# 验证 kubelet 服务状态
# Linux
sudo systemctl status kubelet

# Windows
Get-Service kubelet

# 验证 kubectl 连接
kubectl version --client
kubectl version  # 需要连接服务器
kubectl get nodes
kubectl get pods -A
```

## 常见问题排查

### kubelet 无法启动

```bash
# Linux: 查看日志
sudo journalctl -u kubelet -f
sudo journalctl -u kubelet --since="1 hour ago"

# 检查配置文件
sudo cat /var/lib/kubelet/config.yaml
ls -la /etc/kubernetes/

# Windows: 查看事件日志
Get-WinEvent -LogName "Application" -Source "kubelet" | Select-Object -First 20

# 查看 kubelet 日志文件
Get-Content C:\var\log\kubelet\kubelet.log -Tail 50
```

### 节点 NotReady

```bash
# 检查节点状态
kubectl describe node <node-name>

# 检查 kubelet 配置
kubectl get node <node-name> -o yaml

# 常见原因：
# 1. CNI 插件未安装或配置错误
# 2. kubelet 无法连接到 API Server
# 3. 系统资源不足
```

---

# k8s-cluster-manager（基础集群管理）

## 典型触发场景

- “我有多个集群/多套环境，先帮我确认该操作哪个集群”
- “如何配置 KUBECONFIG 环境变量连接集群”
- “做一次集群巡检/健康检查/容量评估”
- “节点 NotReady、资源紧张、驱逐、证书快过期”
- “要创建 namespace / 配额 / 网络策略 / RBAC”
- “生产变更前需要风险评估与回滚预案”
- “Linux/Windows 上如何安装 kubelet/kubectl/kubeadm”
- “如何将新节点加入集群”

## 多集群选择与防误操作

推荐固定流程（先确认，再执行）：

```bash
# 1) 列出 context
kubectl config get-contexts

# 2) 查看当前 context（必须确认）
kubectl config current-context

# 3) 针对目标操作，显式指定 --context（多集群强烈建议）
kubectl --context <ctx> get ns
```

如果用户没有给出 context，必须先通过问题/线索推断或要求提供（至少给出候选列表与风险提醒），再进入后续步骤。

## 集群巡检（80% 常用项）

### 快速健康快照（只读）

```bash
kubectl --context <ctx> get nodes -o wide
kubectl --context <ctx> get pods -A -o wide
kubectl --context <ctx> get events -A --sort-by=.lastTimestamp
kubectl --context <ctx> top nodes 2>/dev/null || true
kubectl --context <ctx> top pods -A 2>/dev/null || true
```

PowerShell（可选）：

```powershell
kubectl --context <ctx> get nodes -o wide
kubectl --context <ctx> get pods -A -o wide
kubectl --context <ctx> get events -A --sort-by=.lastTimestamp | Select-Object -Last 50
kubectl --context <ctx> top nodes 2>$null
kubectl --context <ctx> top pods -A 2>$null
```

关注点：
- **节点 Ready/压力条件**：MemoryPressure/DiskPressure/PIDPressure/NetworkUnavailable
- **异常 Pod**：`Pending`/`CrashLoopBackOff`/`ImagePullBackOff`/`Evicted`
- **近期 Warning 事件**：调度失败、探针失败、拉镜像失败、驱逐、卷挂载失败

### 命名空间治理（配额/限制）

```bash
# 查看 namespace 配额与限制（如存在）
kubectl --context <ctx> -n <ns> get resourcequota
kubectl --context <ctx> -n <ns> get limitrange
```

建议输出：
- 是否需要设置 `ResourceQuota`/`LimitRange`
- 对应用请求/限制（requests/limits）的约束建议与风险（OOM/CPU throttling/驱逐）

### RBAC 最小权限（提示模板）

在需要变更或批量操作时，优先提示：
- 使用专用 `ServiceAccount`
- 通过 `kubectl auth can-i` 做权限验证

```bash
kubectl --context <ctx> auth can-i get pods -n <ns> --as=system:serviceaccount:<ns>:<sa>
```

---

# k8s-deployer（应用部署与发布）

## 典型触发场景

- “部署一个新服务/更新镜像/改配置/加环境变量/挂载配置”
- “发布失败了（CrashLoopBackOff/探针失败/回滚）”
- “做灰度/金丝雀/分批发布”
- “扩缩容/查看 rollout/回退到上一版本”

## 标准发布流程（建议默认执行）

### 0) 明确发布对象

至少要明确：
- context / namespace
- 工作负载类型：Deployment/StatefulSet/DaemonSet
- 服务暴露：Service/Ingress（如涉及）
- 变更内容：镜像、资源、配置、探针、路由

### 1) 发布前读现状（证据）

```bash
kubectl --context <ctx> -n <ns> get deploy <name> -o wide
kubectl --context <ctx> -n <ns> get deploy <name> -o yaml
kubectl --context <ctx> -n <ns> describe deploy <name>
```

### 2) 变更方式选择（优先级）

- **优先**：声明式（GitOps / `kubectl apply -f` / Kustomize / Helm）
- **次选**：受控的 `kubectl set image`、`kubectl patch`（必须给回滚）
- **避免**：手工改动难以复现的操作（除非应急并记录）

### 3) 执行发布（示例）

#### 镜像更新（Deployment）

```bash
kubectl --context <ctx> -n <ns> set image deploy/<name> <container>=<image:tag>
kubectl --context <ctx> -n <ns> rollout status deploy/<name> --timeout=5m
```

#### 扩缩容

```bash
kubectl --context <ctx> -n <ns> scale deploy/<name> --replicas=<n>
kubectl --context <ctx> -n <ns> get pods -l app=<label> -o wide
```

#### 发布回滚（失败必备）

```bash
kubectl --context <ctx> -n <ns> rollout history deploy/<name>
kubectl --context <ctx> -n <ns> rollout undo deploy/<name>
kubectl --context <ctx> -n <ns> rollout status deploy/<name> --timeout=5m
```

### 4) 发布失败快速诊断（最常见）

```bash
kubectl --context <ctx> -n <ns> get pods -l app=<label> -o wide
kubectl --context <ctx> -n <ns> describe pod <pod>
kubectl --context <ctx> -n <ns> logs <pod> --tail=200
kubectl --context <ctx> -n <ns> logs <pod> --previous --tail=200
kubectl --context <ctx> -n <ns> get events --sort-by=.lastTimestamp | tail -n 30
```

常见根因方向（输出里要落到“证据 -> 结论”）：
- 镜像拉取失败：仓库/权限/Tag/镜像不存在
- 探针失败：readiness/liveness/startup 配置不合理或依赖外部组件
- 资源不足：requests 太高调度失败、limits 太低 OOM
- 配置错误：ConfigMap/Secret 键缺失、挂载路径冲突、环境变量拼写
- Service selector 不匹配：无 endpoints 导致流量失败

## Helm / Kustomize 兼容说明（按需）

如用户明确使用 Helm：
- 必须确认 release、namespace、values 来源
- 输出包含回滚命令（`helm rollback`）

如使用 Kustomize：
- 必须确认 overlay（dev/stage/prod）与渲染结果（避免跨环境误用）

---

# k8s-job-runner（批量作业与一次性任务）

## 典型触发场景

- “在多个集群/多个 namespace 里批量执行一次性任务”
- “触发一批 Job，追踪成功率与失败原因”
- “CronJob 需要立刻跑一次/临时改并发/暂停”
- “批量清理 Completed/Failed 的 Job/Pod”

## 安全执行模型（默认）

### 1) 先定批量范围与并发策略

必须明确：
- 目标 context 列表（多集群）
- namespace 列表
- selector（label）或资源清单
- 并发上限（避免把集群打满）
- 失败策略（遇到失败：停止/跳过/重试）

### 2) Job/CronJob 常用操作

#### 从 CronJob 立刻触发一次

```bash
kubectl --context <ctx> -n <ns> create job --from=cronjob/<cronjob> <job-name>
kubectl --context <ctx> -n <ns> get jobs
kubectl --context <ctx> -n <ns> logs job/<job-name> --tail=200
```

#### 查看 Job 结果与事件

```bash
kubectl --context <ctx> -n <ns> describe job <job-name>
kubectl --context <ctx> -n <ns> get pods -l job-name=<job-name> -o wide
kubectl --context <ctx> -n <ns> describe pod <pod>
```

#### 并发与重试关键字段（建议检查）

检查/建议输出：
- `backoffLimit`（失败重试上限）
- `activeDeadlineSeconds`（最长运行时间）
- `ttlSecondsAfterFinished`（完成后自动清理）
- CronJob 的 `concurrencyPolicy`、`startingDeadlineSeconds`、`suspend`

### 3) 批量清理（谨慎）

只在确认命名空间与选择器后执行，并给出影响面：

```bash
# 清理 Completed 的 Pod（示例：命名空间内）
kubectl --context <ctx> -n <ns> delete pod --field-selector=status.phase==Succeeded

# 清理 Failed 的 Pod
kubectl --context <ctx> -n <ns> delete pod --field-selector=status.phase==Failed
```

> ⚠️ 删除 Job/Pod 可能影响日志留存与审计；优先使用 TTL 或保留关键证据后再清理。

---

# 多集群实战场景剧本（覆盖面导向）

下面剧本用于“多集群 + 交付/运维”高频需求，按默认流程产出结果：

## 场景 A：跨集群发布同一版本并验证

- **输入要素**：context 列表、namespace、workload 名称、镜像 tag、验证 URL/探针
- **策略**：先小流量集群/预发集群验证，再批量扩展；失败立即回滚并保留证据

## 场景 B：某个集群发布后大量 CrashLoopBackOff

- **先读**：pods/events/logs/previous + 对比发布前 spec（镜像/探针/资源/配置）
- **处理**：先止血（暂停 rollout/回滚），再根因定位（探针/配置/资源/依赖）

## 场景 C：批量触发数据修复 Job（多集群多 namespace）

- **先定范围**：context/ns 清单与并发上限
- **执行**：逐集群创建 Job，追踪成功率；失败按策略重试或停止
- **收尾**：汇总结果（成功/失败/耗时），必要时清理资源

## 场景 D：集群节点压力导致驱逐/调度失败

- **证据**：node conditions、events、top、异常 pod 列表
- **处理**：短期扩容/疏散（drain/cordon，谨慎），长期配额与 requests/limits 治理

---

# 日常高频查询场景速查（Q&A）

## 场景 1：节点资源可用量查询

### 查询所有节点的 CPU/内存可用量

```bash
# 方法 1：使用 kubectl top（需要 metrics-server）
kubectl top nodes

# 方法 2：查看节点容量和可分配资源
kubectl get nodes -o custom-columns=NODE:.metadata.name,CPU_CAPACITY:.status.capacity.cpu,CPU_ALLOCATABLE:.status.allocatable.cpu,MEM_CAPACITY:.status.capacity.memory,MEM_ALLOCATABLE:.status.allocatable.memory

# 方法 3：查看节点资源使用详情（含已分配/剩余）
kubectl describe nodes | grep -E "(Name:|Allocated resources:|Capacity:|Allocatable:|cpu|memory)"
```

### 筛选可用内存低于 2GB 的节点

```bash
# 使用 kubectl 配合 jsonpath 和 awk 筛选
kubectl get nodes -o json | jq -r '.items[] | select(.status.allocatable.memory | gsub("Ki"; "") | tonumber < 2097152) | .metadata.name'

# 或使用自定义输出配合脚本筛选
kubectl get nodes -o custom-columns=NODE:.metadata.name,MEM_ALLOCATABLE:.status.allocatable.memory | awk '$2 ~ /Ki$/ {mem=substr($2,1,length($2)-2); if (mem < 2097152) print $1 " 内存不足: " $2}'
```

---

## 场景 2：Pod 状态与数据筛选

### 查询指定 namespace 下 Running 状态的 Pod，显示重启次数和所属节点

```bash
# 单条命令实现
kubectl get pods -n default --field-selector=status.phase=Running -o custom-columns=POD:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,NODE:.spec.nodeName,STATUS:.status.phase

# 或更详细版本（显示所有容器重启次数）
kubectl get pods -n default --field-selector=status.phase=Running -o custom-columns=POD:.metadata.name,RESTARTS:".status.containerStatuses[*].restartCount",NODE:.spec.nodeName,READY:".status.containerStatuses[*].ready"
```

---

## 场景 3：Service/Ingress 关联查询

### 查询 Service 绑定的 Pod

```bash
# 1) 查看 Service 详情和 selector
kubectl get svc nginx-svc -n test -o yaml

# 2) 通过 selector 查询关联的 Pod
# 假设 selector 是 app=nginx
kubectl get pods -n test -l app=nginx -o wide

# 3) 查看 Service 的 endpoints（验证绑定关系）
kubectl get endpoints nginx-svc -n test
kubectl describe svc nginx-svc -n test
```

### 验证 Ingress 配置

```bash
# 查看 Ingress 规则
kubectl get ingress -n test
kubectl describe ingress <ingress-name> -n test

# 查看 Ingress 后端服务映射
kubectl get ingress -n test -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .spec.rules[*]}{"  Host: "}{.host}{"\n"}{range .http.paths[*]}{"    Path: "}{.path}{" -> Service: "}{.backend.service.name}{":"}{.backend.service.port.number}{"\n"}{end}{end}{end}'

# 验证 Ingress Controller 状态
kubectl get pods -n ingress-nginx -o wide  # 或其他 ingress controller namespace
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller --tail=100
```

---

## 场景 4：多命名空间资源统计

### 统计多个 namespace 的 Pod 总数（按状态分组）

```bash
# Bash 脚本实现
for ns in dev test prod; do
  echo "=== Namespace: $ns ==="
  kubectl get pods -n $ns --field-selector=status.phase=Running -o name | wc -l | xargs -I {} echo "Running: {}"
  kubectl get pods -n $ns --field-selector=status.phase=Pending -o name | wc -l | xargs -I {} echo "Pending: {}"
  kubectl get pods -n $ns --field-selector=status.phase=Failed -o name | wc -l | xargs -I {} echo "Failed: {}"
done

# 或使用 json 输出统计
kubectl get pods -A -o json | jq -r '.items | group_by(.metadata.namespace) | .[] | {namespace: .[0].metadata.namespace, running: map(select(.status.phase=="Running")) | length, pending: map(select(.status.phase=="Pending")) | length, failed: map(select(.status.phase=="Failed")) | length}'
```

---

## 场景 5：ConfigMap/Secret 数据管理

### 从本地文件创建 ConfigMap

```bash
# 从文件创建 ConfigMap
kubectl create configmap app-config -n prod --from-file=app-config.yaml

# 或从文件内容创建（指定 key 名）
kubectl create configmap app-config -n prod --from-file=config.yaml=app-config.yaml

# 验证创建
kubectl get configmap app-config -n prod -o yaml
```

### 查询 ConfigMap 是否被 Pod 挂载使用

```bash
# 方法 1：查询挂载了该 ConfigMap 的 Pod
kubectl get pods -n prod -o json | jq -r '.items[] | select(.spec.volumes[].configMap.name=="app-config") | .metadata.name'

# 方法 2：使用 describe 查看 Pod 详情
kubectl describe pod <pod-name> -n prod | grep -A5 "Volumes\|app-config"

# 方法 3：查看 Pod 中环境变量引用
kubectl get pods -n prod -o json | jq -r '.items[] | select(.spec.containers[].envFrom[].configMapRef.name=="app-config" or .spec.containers[].env[].valueFrom.configMapKeyRef.name=="app-config") | .metadata.name'
```

---

## 场景 6：Job 执行结果查询与管理

### 查询 Job 执行日志

```bash
# 查看 Job 状态
kubectl get job data-backup -o wide
kubectl describe job data-backup

# 查看 Job 关联的 Pod
kubectl get pods -l job-name=data-backup -o wide

# 查看日志
kubectl logs -l job-name=data-backup --tail=200

# 如果 Job 有多个 Pod，查看所有 Pod 日志
for pod in $(kubectl get pods -l job-name=data-backup -o name); do
  echo "=== Logs from $pod ==="
  kubectl logs $pod --tail=100
done
```

### 删除并重新提交失败的 Job

```bash
# 方法 1：先删除再重新创建（保留 Job 定义）
kubectl get job data-backup -o yaml > data-backup-job.yaml
kubectl delete job data-backup
kubectl apply -f data-backup-job.yaml

# 方法 2：强制替换（不保留历史）
kubectl replace --force -f data-backup-job.yaml

# 方法 3：使用 kubectl run 快速重新创建
kubectl create job data-backup-$(date +%s) --from=cronjob/data-backup
```

---

## 场景 7：节点标签管理与资源筛选

### 给节点添加标签

```bash
# 添加标签
kubectl label nodes node-01 role=db

# 验证标签
kubectl get nodes node-01 --show-labels

# 查看所有 role=db 的节点
kubectl get nodes -l role=db
```

### 查询带标签节点上运行的 Pod

```bash
# 步骤 1：获取所有 role=db 的节点名称
kubectl get nodes -l role=db -o name

# 步骤 2：查询这些节点上的所有 Pod（所有 namespace）
for node in $(kubectl get nodes -l role=db -o jsonpath='{.items[*].metadata.name}'); do
  echo "=== Pods on node: $node ==="
  kubectl get pods --all-namespaces --field-selector spec.nodeName=$node -o wide
done

# 或使用 json 输出一次性查询
kubectl get pods --all-namespaces -o json | jq -r --argjson nodes "$(kubectl get nodes -l role=db -o json | jq -r '.items[].metadata.name' | jq -R -s -c 'split("\n")[:-1]')" '.items[] | select(.spec.nodeName as $n | $nodes | index($n)) | [.metadata.namespace, .metadata.name, .spec.nodeName] | @tsv'
```

---

## 场景 8：资源限额配置与验证

### 为 namespace 配置默认资源限额

```bash
# 创建 LimitRange 配置
kubectl apply -f - <<EOF
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: dev
spec:
  limits:
  - default:
      cpu: "0.5"
      memory: "512Mi"
    defaultRequest:
      cpu: "0.1"
      memory: "128Mi"
    type: Container
EOF

# 或创建 ResourceQuota 限制 namespace 总资源
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "100"
EOF
```

### 验证配置是否生效

```bash
# 查看 LimitRange
kubectl get limitrange -n dev -o yaml

# 查看 ResourceQuota
kubectl get resourcequota -n dev -o yaml
kubectl describe resourcequota dev-quota -n dev

# 验证新创建的 Pod 是否继承默认限额
kubectl run test-pod --image=nginx -n dev --dry-run=client -o yaml | kubectl apply -f -
kubectl get pod test-pod -n dev -o jsonpath='{.spec.containers[0].resources}'
kubectl delete pod test-pod -n dev
```

---

## 场景 9：日志快速查询与筛选

### 查询过去 10 分钟内包含 "error" 的日志

```bash
# 使用 --since 参数查询最近 10 分钟的日志
kubectl logs nginx-xxx -n default --since=10m | grep "error"

# 只显示日志内容不显示 Pod 名称（grep 本身不显示 Pod 名）
kubectl logs -l app=nginx -n default --since=10m | grep "error"

# 如果 Pod 有多个容器，指定容器名
kubectl logs nginx-xxx -c <container-name> -n default --since=10m | grep -i "error"

# 查看之前容器的日志（如果 Pod 重启过）
kubectl logs nginx-xxx -n default --previous --since=10m | grep -i "error"

# 多个 Pod 聚合日志（使用 label 选择器）
kubectl logs -l app=nginx -n default --since=10m --all-containers=true | grep -i "error"
```

### 高级日志查询

```bash
# 实时跟踪日志
kubectl logs -f nginx-xxx -n default

# 查看最后 N 行
kubectl logs nginx-xxx -n default --tail=100

# 组合查询：最近 10 分钟、包含 error、最后 50 行
kubectl logs nginx-xxx -n default --since=10m --tail=50 | grep -i "error"
```

---

## 场景 10：多集群切换与查询

### 快速切换到指定集群并查询

```bash
# 方法 1：使用 kubectx（推荐，如有安装）
kubectx prod
kubectl get ns

# 方法 2：使用 kubectl config
# 列出所有 context
kubectl config get-contexts

# 切换到 prod 集群
kubectl config use-context prod

# 验证当前 context
kubectl config current-context

# 查询 namespace 列表
kubectl get namespaces
```

### 不切换 context 直接操作指定集群

```bash
# 推荐方式：使用 --context 参数，避免误操作
kubectl --context=prod get namespaces
kubectl --context=prod get pods -A

# 跨集群对比查询
for ctx in dev prod; do
  echo "=== Cluster: $ctx ==="
  kubectl --context=$ctx get nodes -o wide
done
```

---

# 最小信息收集清单（用户输入不全时用）

当用户只说“帮我部署/排障/跑任务”但信息不全时，优先收集：
- context（或环境名：dev/stage/prod）与集群列表
- namespace
- 资源类型与名称（deploy/sts/job 等）
- 期望结果与截止时间（是否应急）
- 允许的变更范围（是否允许回滚/扩容/重启）

