package main

import (
	"flag"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/client/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/pkg/logger"
)

func main() {
	var configPath string
	flag.StringVar(&configPath, "c", "./client.yaml", "path to client config file")
	flag.Parse()

	cfg := config.MustLoadConfig(configPath)
	cfg.InitLogger()

	logger.Infof("PilotGo client starting, client_id=%s, server=%s", cfg.ClientID(), cfg.Server.Addr)

	// 当前仅作为配置加载与日志初始化的最小入口

	select {}
}
