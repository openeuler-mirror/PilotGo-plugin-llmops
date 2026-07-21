package http

import (
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/http/handler"
	mcphandler "gitee.com/openeuler/PilotGo-plugin-llmops/server/server/http/mcp_handler"
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
			projectGroup.GET("/:id/operation/scripts", handler.ListOperationScripts)
			projectGroup.POST("/:id/operation/scripts", handler.CreateOperationScript)
			projectGroup.PUT("/:id/operation/scripts/:sid", handler.UpdateOperationScript)
			projectGroup.DELETE("/:id/operation/scripts/:sid", handler.DeleteOperationScript)
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

		topologyGroup := apiGroup.Group("/topology")
		{
			topologyGroup.GET("", handler.ListTopologyConfig)
			topologyGroup.PUT("", handler.SaveTopologyConfig)
			topologyGroup.DELETE("/:id", handler.DeleteTopologyConfig)
		}
	}
	return router
}

func registerMCPTools(srv *mcp.Server) {
	mcp.AddTool(srv, &mcp.Tool{Name: "greet", Description: "say hi"}, mcphandler.SayHi)
}
