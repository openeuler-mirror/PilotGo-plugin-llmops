package topology

import (
	"context"
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/internal/dao"
)

type TopologyService struct {
	td *dao.TopologyDao
}

var (
	globalTopologyService *TopologyService
)

func GetTopologyService() *TopologyService {
	if globalTopologyService == nil {
		globalTopologyService = &TopologyService{}
	}
	return globalTopologyService
}

func (s *TopologyService) Name() string {
	return "Topology Service"
}

func (s *TopologyService) Run(ctx context.Context) error {
	s.td = dao.NewTopologyDao()
	if err := db.AutoMigrate(&dao.TopologyConfig{}); err != nil {
		return errors.New("failed to migrate topology database: " + err.Error())
	}

	<-ctx.Done()
	logger.Infof("service stopped: %s", s.Name())
	return nil
}

// List 获取拓扑配置列表，projectID > 0 时按项目过滤
func (s *TopologyService) List(projectID int) ([]*TopologyConfigDTO, error) {
	if s.td == nil {
		return nil, errors.New("topology service not initialized")
	}

	var items []*dao.TopologyConfig
	var err error
	if projectID > 0 {
		items, err = s.td.ListByProjectID(projectID)
	} else {
		items, err = s.td.List()
	}
	if err != nil {
		return nil, err
	}

	// 转换为DTO列表
	result := make([]*TopologyConfigDTO, len(items))
	for i, item := range items {
		result[i] = &TopologyConfigDTO{
			ID:        item.ID,
			ProjectID: item.ProjectID,
			HostID:    item.HostID,
			Process:   item.Process,
			CreatedAt: item.CreatedAt,
			UpdatedAt: item.UpdatedAt,
		}
	}

	return result, nil
}

// Save 保存拓扑配置：ID > 0 的更新，ID == 0 的新增
func (s *TopologyService) Save(items []*TopologyConfigDTO) error {
	if s.td == nil {
		return errors.New("topology service not initialized")
	}

	var toUpdate []*dao.TopologyConfig
	var toInsert []*dao.TopologyConfig
	for _, item := range items {
		if item == nil {
			continue
		}
		cfg := &dao.TopologyConfig{
			ID:        item.ID,
			ProjectID: item.ProjectID,
			HostID:    item.HostID,
			Process:   item.Process,
			CreatedAt: item.CreatedAt,
			UpdatedAt: item.UpdatedAt,
		}
		if cfg.ID > 0 {
			toUpdate = append(toUpdate, cfg)
		} else {
			toInsert = append(toInsert, cfg)
		}
	}

	if len(toUpdate) > 0 {
		if err := s.td.BatchUpdate(toUpdate); err != nil {
			return err
		}
	}
	if len(toInsert) > 0 {
		if err := s.td.BatchInsert(toInsert); err != nil {
			return err
		}
	}

	return nil
}

// Delete 删除拓扑配置
func (s *TopologyService) Delete(id int64) error {
	if s.td == nil {
		return errors.New("topology service not initialized")
	}
	if id <= 0 {
		return errors.New("invalid id")
	}
	return s.td.Delete(id)
}
