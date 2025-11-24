package handler

import (
	"net/http"
	"strconv"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/audit"
	"github.com/gin-gonic/gin"
)

var auditSrv = audit.GetAuditService()

func ListAuditByProjectID(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	items, err := auditSrv.ListAuditsByProjectID(c.Request.Context(), id)
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	res := make([]gin.H, len(items))
	for i, a := range items {
		res[i] = gin.H{
			"id":          a.ID,
			"time":        a.CreatedAt,
			"operator":    a.Actor,
			"component":   a.Target,
			"description": a.Action,
		}
	}
	Response(c, res)
}

type listAuditQueryReq struct {
	ProjectID  string `form:"project_id"`
	Actor      string `form:"actor"`
	ActionType string `form:"action_type"`
	Target     string `form:"target"`
}

func ListAuditByFilters(c *gin.Context) {
	var req listAuditQueryReq
	if err := c.ShouldBindQuery(&req); err != nil {
		ResponseError(c, http.StatusBadRequest, "invalid query")
		return
	}
	var pid *int
	if req.ProjectID != "" {
		if n, err := strconv.Atoi(req.ProjectID); err == nil && n > 0 {
			pid = &n
		} else {
			ResponseError(c, http.StatusBadRequest, "invalid project_id")
			return
		}
	}
	items, err := auditSrv.ListAuditsByFilters(c.Request.Context(), &audit.ListAuditReq{
		ProjectID:  pid,
		Actor:      req.Actor,
		ActionType: req.ActionType,
		Target:     req.Target,
	})
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, items)
}
