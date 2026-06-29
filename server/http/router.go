package http

import (
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/http/handler"
	mcphandler "gitee.com/openeuler/PilotGo-plugin-llmops/server/http/mcp_handler"
	"github.com/gin-gonic/gin"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func registerRouter(router *gin.Engine) *gin.Engine {
	router.GET("/ping", handler.Ping)

	apiGroup := router.Group("/api")
	{
		projectGroup := apiGroup.Group("/project")
		{
			projectGroup.POST("", handler.CreateProject)
			projectGroup.DELETE("/:id", handler.DeleteProject)
			projectGroup.GET("", handler.ListProjects)
			projectGroup.GET("/:id", handler.GetProject)
			projectGroup.PUT("/:id", handler.UpdateProject)
			projectGroup.GET("/:id/audit/logs", handler.ListAuditByProjectID)
			projectGroup.GET("/:id/knowledge/files", handler.ListKnowledge)
		}

		knowledgeGroup := apiGroup.Group("/knowledge")
		{
			knowledgeGroup.POST("/upload", handler.UploadKnowledge)
			knowledgeGroup.GET("/download", handler.DownloadKnowledge)
			knowledgeGroup.GET("/link", handler.PresignKnowledge)
			knowledgeGroup.DELETE("/:id", handler.DeleteKnowledge)
		}

		auditGroup := apiGroup.Group("/audit")
		{
			auditGroup.GET("/logs", handler.ListAuditByFilters)
		}
	}
	return router
}

func registerMCPTools(srv *mcp.Server) {
	mcp.AddTool(srv, &mcp.Tool{Name: "greet", Description: "say hi"}, mcphandler.SayHi)
}
