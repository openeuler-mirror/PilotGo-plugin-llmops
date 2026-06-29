package topology

// TopologyConfigDTO 拓扑配置实体
type TopologyConfigDTO struct {
	ID        int64  `json:"id"`
	ProjectID int    `json:"project_id"`
	HostID    string `json:"host_id"`
	Process   string `json:"process"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}
