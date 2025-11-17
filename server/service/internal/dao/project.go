package dao

import (
	"errors"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gorm.io/gorm"
)

// Project 项目模型
type Project struct {
	ID        int    `json:"id" gorm:"primaryKey;autoIncrement"`
	Name      string `json:"name" gorm:"size:255;not null"`
	Desc      string `json:"desc" gorm:"size:1000"`
	CreatedAt string `json:"created_at" gorm:"varchar(255)"`
	UpdatedAt string `json:"updated_at" gorm:"varchar(255)"`
}

// TableName 指定表名
func (Project) TableName() string {
	return "projects"
}

// ProjectDao 项目数据访问对象
type ProjectDao struct {
	db *gorm.DB
}

// NewProjectDao 创建项目数据访问对象实例
func NewProjectDao() *ProjectDao {
	return &ProjectDao{
		db: db.GetDB(),
	}
}

// Create 添加项目
func (d *ProjectDao) Create(project *Project) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	return d.db.Create(project).Error
}

// Update 更新项目
func (d *ProjectDao) Update(project *Project) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	return d.db.Save(project).Error
}

// Delete 删除项目
func (d *ProjectDao) Delete(id int) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	result := d.db.Delete(&Project{}, id)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errors.New("project not found")
	}
	return nil
}

// GetByID 根据ID获取项目
func (d *ProjectDao) GetByID(id int) (*Project, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var project Project
	err := d.db.First(&project, id).Error
	if err != nil {
		return nil, err
	}
	return &project, nil
}

// List 获取项目列表
func (d *ProjectDao) List() ([]*Project, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var projects []*Project
	err := d.db.Find(&projects).Error
	return projects, err
}
