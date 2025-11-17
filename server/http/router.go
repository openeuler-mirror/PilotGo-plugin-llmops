package http

import (
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/http/handler"
	mcphandler "gitee.com/openeuler/PilotGo-plugin-llmops/server/http/mcp_handler"
	"github.com/gin-gonic/gin"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func registerRouter(router *gin.Engine) *gin.Engine {
	router.GET("/ping", handler.Ping)

	projectGroup := router.Group("/projects")
	{
		projectGroup.POST("", handler.CreateProject)
		projectGroup.DELETE("/:id", handler.DeleteProject)
		projectGroup.GET("", handler.ListProjects)
		projectGroup.GET("/:id", handler.GetProject)
	}
	return router
}

func registerMCPTools(srv *mcp.Server) {
	mcp.AddTool(srv, &mcp.Tool{Name: "greet", Description: "say hi"}, mcphandler.SayHi)
}
