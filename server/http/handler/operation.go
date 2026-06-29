package handler

import (
	"net/http"
	"strconv"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/operation"
	"github.com/gin-gonic/gin"
)

var operationSrv = operation.GetOperationService()

type operationScriptReq struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Content     string `json:"content"`
	UpdatedBy   string `json:"updated_by"`
}

func ListOperationScripts(c *gin.Context) {
	projectID, err := strconv.Atoi(c.Param("id"))
	if err != nil || projectID <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid project id")
		return
	}
	data, err := operationSrv.List(projectID)
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, data)
}

func CreateOperationScript(c *gin.Context) {
	projectID, err := strconv.Atoi(c.Param("id"))
	if err != nil || projectID <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid project id")
		return
	}
	var req operationScriptReq
	if err := c.ShouldBindJSON(&req); err != nil || req.Name == "" {
		ResponseError(c, http.StatusBadRequest, "invalid request")
		return
	}
	if err := operationSrv.Create(projectID, req.Name, req.Description, req.Content, req.UpdatedBy); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "created")
}

func UpdateOperationScript(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("sid"), 10, 64)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	var req operationScriptReq
	if err := c.ShouldBindJSON(&req); err != nil || req.Name == "" {
		ResponseError(c, http.StatusBadRequest, "invalid request")
		return
	}
	if err := operationSrv.Update(id, req.Name, req.Description, req.Content, req.UpdatedBy); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "updated")
}

func DeleteOperationScript(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("sid"), 10, 64)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	if err := operationSrv.Delete(id); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "deleted")
}
