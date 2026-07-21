package dao

import (
	"errors"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/db"
	"gorm.io/gorm"
)

type OperationScript struct {
	ID          int64  `json:"id" gorm:"primaryKey"`
	ProjectID   int    `json:"project_id" gorm:"not null;index"`
	Name        string `json:"name" gorm:"size:255;not null"`
	Description string `json:"description" gorm:"size:1000"`
	Content     string `json:"content" gorm:"type:text"`
	UpdatedBy   string `json:"updated_by" gorm:"size:255"`
	CreatedAt   string `json:"created_at" gorm:"type:varchar(32)"`
	UpdatedAt   string `json:"updated_at" gorm:"type:varchar(32)"`
}

func (OperationScript) TableName() string {
	return "operation_script"
}

type OperationDao struct {
	db *gorm.DB
}

func NewOperationDao() *OperationDao {
	return &OperationDao{db: db.GetDB()}
}

func (d *OperationDao) Create(s *OperationScript) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	if s.CreatedAt == "" {
		s.CreatedAt = now
	}
	s.UpdatedAt = now
	return d.db.Create(s).Error
}

func (d *OperationDao) Update(s *OperationScript) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	s.UpdatedAt = time.Now().Format("2006-01-02 15:04:05")
	return d.db.Save(s).Error
}

func (d *OperationDao) Delete(id int64) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	result := d.db.Delete(&OperationScript{}, id)
	if result.Error != nil {
		return result.Error
	}
	return nil
}

func (d *OperationDao) GetByID(id int64) (*OperationScript, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var s OperationScript
	err := d.db.First(&s, id).Error
	if err != nil {
		return nil, err
	}
	return &s, nil
}

func (d *OperationDao) ListByProjectID(projectID int) ([]*OperationScript, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*OperationScript
	err := d.db.Where("project_id = ?", projectID).Find(&items).Error
	return items, err
}
