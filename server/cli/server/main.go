package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/http"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
)

func main() {
	fmt.Println("Starting server...")
	config.InitConfig()
	logger.Init(&config.GetConfig().Log)

	// 启动HTTP服务
	go func() {
		if err := http.RunServer(); err != nil {
			logger.Fatal("Failed to start HTTP server: ", err)
		}
	}()

	// 监听信号
	ch := make(chan os.Signal, 1)
	signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
	<-ch
	logger.Info("Shutting down...")

	// 停止HTTP服务
	http.StopServer()
	logger.Info("Server stopped.")
}
