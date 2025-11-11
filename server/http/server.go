package http

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/config"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"github.com/gin-gonic/gin"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

var srv *http.Server
var mcpSrv *mcp.Server

func RunServer() error {
	// http server handler
	router := gin.Default()
	httpHandler := registerRouter(router)

	// MCP streamable HTTP handler.
	mcpSrv = mcp.NewServer(&mcp.Implementation{Name: "greeter", Version: "v0.0.1"}, nil)
	registerMCPTools(mcpSrv)
	mcpHandler := mcp.NewStreamableHTTPHandler(func(req *http.Request) *mcp.Server {
		return mcpSrv
	}, nil)

	addr := fmt.Sprintf("%s:%d", config.GetConfig().Server.Host, config.GetConfig().Server.Port)
	srv = &http.Server{
		Addr:    addr,
		Handler: combineHandler(httpHandler, mcpHandler),
	}
	logger.Info("HTTP server is running on: " + "http://" + addr)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}
	return nil
}

func combineHandler(httpHandler *gin.Engine, mcpHandler *mcp.StreamableHTTPHandler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/mcp/") {
			mcpHandler.ServeHTTP(w, r)
		} else {
			httpHandler.ServeHTTP(w, r)
		}
	})
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
