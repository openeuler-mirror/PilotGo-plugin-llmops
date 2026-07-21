package handler

import (
	"net/http"
	"strconv"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/service/project"
	"github.com/gin-gonic/gin"
)

var projectSrv = project.GetProjectService()

type createProjectReq struct {
	Name string `json:"name"`
	Desc string `json:"desc"`
}

func CreateProject(c *gin.Context) {
	var req createProjectReq
	if err := c.ShouldBindJSON(&req); err != nil || req.Name == "" {
		ResponseError(c, http.StatusBadRequest, "invalid request")
		return
	}
	if err := projectSrv.AddProject(req.Name, req.Desc); err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	ResponseOK(c, "created")
}

type updateProjectReq struct {
	Name string `json:"name"`
	Desc string `json:"desc"`
}

func UpdateProject(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}

	var req updateProjectReq
	if err := c.ShouldBindJSON(&req); err != nil || req.Name == "" {
		ResponseError(c, http.StatusBadRequest, "invalid request")
		return
	}

	if err := projectSrv.UpdateProject(id, req.Name, req.Desc); err != nil {
		ResponseError(c, http.StatusNotFound, err.Error())
		return
	}
	ResponseOK(c, "updated")
}

func DeleteProject(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	if err := projectSrv.DeleteProject(id); err != nil {
		ResponseError(c, http.StatusNotFound, err.Error())
		return
	}
	ResponseOK(c, "deleted")
}

func ListProjects(c *gin.Context) {
	projects, err := projectSrv.GetProjectsList()
	if err != nil {
		ResponseError(c, http.StatusInternalServerError, err.Error())
		return
	}
	Response(c, projects)
}

func GetProject(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.Atoi(idStr)
	if err != nil || id <= 0 {
		ResponseError(c, http.StatusBadRequest, "invalid id")
		return
	}
	p, err := projectSrv.GetProjectByID(id)
	if err != nil {
		ResponseError(c, http.StatusNotFound, err.Error())
		return
	}
	Response(c, p)
}
