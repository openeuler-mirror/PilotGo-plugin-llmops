package service

import (
    "context"

    "gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
    "gitee.com/openeuler/PilotGo-plugin-llmops/server/service/audit"
    "gitee.com/openeuler/PilotGo-plugin-llmops/server/service/knowledge"
    "gitee.com/openeuler/PilotGo-plugin-llmops/server/service/operation"
    "gitee.com/openeuler/PilotGo-plugin-llmops/server/service/project"
    "gitee.com/openeuler/PilotGo-plugin-llmops/server/service/topology"
    "github.com/sourcegraph/conc"
)

type Service interface {
	Name() string
	// Run 启动服务并阻塞直到服务停止
	Run(ctx context.Context) error
}

var (
	services map[string]Service
	ctx      context.Context
	cancel   context.CancelFunc
	wg       conc.WaitGroup
)

func registerService(s Service) {
	if services == nil {
		services = make(map[string]Service)
	}

	if _, ok := services[s.Name()]; ok {
		logger.Fatal("Service name already registered: ", s.Name())
	}

	services[s.Name()] = s
}

func registerServices() {
    registerService(project.GetProjectService())
    registerService(knowledge.GetKnowledgeService())
    registerService(audit.GetAuditService())
    registerService(topology.GetTopologyService())
    registerService(operation.GetOperationService())
}

func StartServices() error {
	ctx, cancel = context.WithCancel(context.Background())

	registerServices()

	// 使用conc.WaitGroup来管理所有服务
	for _, s := range services {
		wg.Go(func() {
			logger.Infof("service starting: %s", s.Name())
			if err := s.Run(ctx); err != nil {
				logger.Errorf("Failed to start service: %v", err)
			}
		})
	}

	return nil
}

func StopServices() error {
	// 取消上下文，通知所有服务停止
	cancel()

	// 等待所有服务优雅退出
	wg.Wait()
	logger.Infof("All services stopped")

	return nil
}
