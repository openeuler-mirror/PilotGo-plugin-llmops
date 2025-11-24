package audit

import (
	"context"
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/internal/dao"
)

type AuditService struct {
	ad *dao.AuditDao
}

var (
	globalAuditService *AuditService
)

func GetAuditService() *AuditService {
	if globalAuditService == nil {
		globalAuditService = &AuditService{}
	}
	return globalAuditService
}

func (s *AuditService) Name() string {
	return "Audit Service"
}

func (s *AuditService) Run(ctx context.Context) error {
	s.ad = dao.NewAuditDao()
	if err := db.AutoMigrate(&dao.Audit{}); err != nil {
		return errors.New("failed to migrate audit database: " + err.Error())
	}
	<-ctx.Done()
	logger.Infof("service stopped: %s", s.Name())
	return nil
}
