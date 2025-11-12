package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/http"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service"
)

func main() {
	fmt.Println("starting llmops server...")
	config.InitConfig()
	logger.Init(&config.GetConfig().Log)

	// 初始化数据库连接
	if err := db.InitDB(); err != nil {
		logger.Fatal("failed to initialize database: ", err)
	}
	defer db.Close()

	// 数据库迁移将在service层处理
	logger.Info("database initialized successfully")

	if err := service.StartServices(); err != nil {
		logger.Fatal("failed to start services: ", err)
	}

	// 启动HTTP服务
	go func() {
		if err := http.RunServer(); err != nil {
			logger.Fatal("failed to start HTTP server: ", err)
		}
	}()

	// 监听信号
	ch := make(chan os.Signal, 1)
	signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
	<-ch
	logger.Info("shutting down...")

	// 停止HTTP服务
	if err := http.StopServer(); err != nil {
		logger.Error("failed to stop HTTP server: ", err)
	}

	// 停止所有服务
	if err := service.StopServices(); err != nil {
		logger.Error("failed to stop services: ", err)
	}
	logger.Info("llmops server stopped.")
}
