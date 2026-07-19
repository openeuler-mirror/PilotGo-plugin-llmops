package handler

import (
	"net/http"
	"strconv"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/service/topology"
	"github.com/gin-gonic/gin"
)

var topologySrv = topology.GetTopologyService()

func ListTopologyConfig(c *gin.Context) {
	projectID := 0
	if idStr := c.Query("project_id"); idStr != "" {
		if id, err := strconv.Atoi(idStr); err == nil {
			projectID = id
		}
	}

	data, err := topologySrv.List(projectID)
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, data)
}

func SaveTopologyConfig(c *gin.Context) {
	var items []*topology.TopologyConfigDTO
	if err := c.ShouldBindJSON(&items); err != nil {
		ResponseError(c, http.StatusBadRequest, "invalid request")
		return
	}
	if err := topologySrv.Save(items); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "saved")
}

func DeleteTopologyConfig(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	if err := topologySrv.Delete(id); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "deleted")
}
