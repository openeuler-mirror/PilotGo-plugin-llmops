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
