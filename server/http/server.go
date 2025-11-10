package http

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"github.com/gin-gonic/gin"
)

var srv *http.Server

func RunServer() error {
	router := gin.Default()
	registerRouter(router)

	addr := fmt.Sprintf("%s:%d", config.GetConfig().Server.Host, config.GetConfig().Server.Port)
	srv = &http.Server{
		Addr:    addr,
		Handler: router,
	}
	logger.Info("HTTP server is running on: " + "http://" + addr)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

func StopServer() error {
	if srv == nil {
		return nil
	}
	logger.Info("Shutting down HTTP server...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()
	err := srv.Shutdown(ctx)
	if err != nil {
		return err
	}
	srv = nil
	return nil
}
