package http

import (
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/http/handler"
	"github.com/gin-gonic/gin"
)

func registerRouter(router *gin.Engine) {
	router.GET("/ping", handler.Ping)
}
