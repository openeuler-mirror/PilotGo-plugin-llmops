package project

import (
	"context"
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/logger"
	"gitee.com/openeuler/PilotGo-plugin-llmops/server/service/internal/dao"
)

// ProjectService 项目服务
type ProjectService struct {
	projectDao *dao.ProjectDao
}

// NewProjectService 创建项目服务实例
func NewProjectService() *ProjectService {
	return &ProjectService{
		projectDao: dao.NewProjectDao(),
	}
}

func (s *ProjectService) Name() string {
	return "Project Service"
}

func (s *ProjectService) Run(ctx context.Context) error {
	// 在服务启动时执行数据库迁移
	if err := db.AutoMigrate(&dao.Project{}); err != nil {
		return errors.New("failed to migrate project database: " + err.Error())
	}

	// 等待系统退出信号
	<-ctx.Done()

	// TODO：添加服务退出逻辑
	logger.Infof("service stopped: %s", s.Name())
	return nil
}

// AddProject 添加项目
func (s *ProjectService) AddProject(name, desc string) error {
	if name == "" {
		return errors.New("project name cannot be empty")
	}

	// 创建项目模型
	project := &dao.Project{
		Name: name,
		Desc: desc,
	}

	// 调用dao层添加项目
	err := s.projectDao.Create(project)
	if err != nil {
		logger.Errorf("failed to add project: %v", err)
		return err
	}

	return nil
}

// DeleteProject 删除项目
func (s *ProjectService) DeleteProject(id int) error {
	if id <= 0 {
		return errors.New("invalid project id")
	}

	// 调用dao层删除项目
	return s.projectDao.Delete(id)
}

// getProjectsList 内部方法，获取项目列表并返回错误
func (s *ProjectService) GetProjectsList() ([]*Project, error) {
	// 调用dao层获取项目列表
	projects, err := s.projectDao.List()
	if err != nil {
		return nil, err
	}

	// 转换为DTO列表
	result := make([]*Project, len(projects))
	for i, p := range projects {
		result[i] = &Project{
			ID:        p.ID,
			Name:      p.Name,
			Desc:      p.Desc,
			CreatedAt: p.CreatedAt.Format("2006-01-02 15:04:05"),
			UpdatedAt: p.UpdatedAt.Format("2006-01-02 15:04:05"),
		}
	}

	return result, nil
}

// GetProjectByID 根据ID获取项目
func (s *ProjectService) GetProjectByID(id int) (*Project, error) {
	if id <= 0 {
		return nil, errors.New("invalid project id")
	}

	// 调用dao层获取项目
	project, err := s.projectDao.GetByID(id)
	if err != nil {
		return nil, err
	}

	// 转换为DTO
	return &Project{
		ID:        project.ID,
		Name:      project.Name,
		Desc:      project.Desc,
		CreatedAt: project.CreatedAt.Format("2006-01-02 15:04:05"),
		UpdatedAt: project.UpdatedAt.Format("2006-01-02 15:04:05"),
	}, nil
}
