package operation

import (
	"context"
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/internal/dao"
)

type OperationService struct {
	od *dao.OperationDao
}

var (
	globalOperationService *OperationService
)

func GetOperationService() *OperationService {
	if globalOperationService == nil {
		globalOperationService = &OperationService{}
	}
	return globalOperationService
}

func (s *OperationService) Name() string {
	return "Operation Service"
}

func (s *OperationService) Run(ctx context.Context) error {
	s.od = dao.NewOperationDao()
	if err := db.AutoMigrate(&dao.OperationScript{}); err != nil {
		return errors.New("failed to migrate operation database: " + err.Error())
	}

	<-ctx.Done()
	logger.Infof("service stopped: %s", s.Name())
	return nil
}
