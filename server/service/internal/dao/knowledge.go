package dao

import (
	"errors"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gorm.io/gorm"
)

type Knowledge struct {
	ID        int64  `json:"id" gorm:"primaryKey"`
	ProjectID int    `json:"project_id" gorm:"not null;index"`
	Object    string `json:"object" gorm:"size:512;not null"`
	FileName  string `json:"file_name" gorm:"size:255;not null"`
	Uploader  string `json:"uploader" gorm:"size:255"`
	Desc      string `json:"desc" gorm:"size:1000"`
	CreatedAt string `json:"created_at" gorm:"type:varchar(32)"`
	UpdatedAt string `json:"updated_at" gorm:"type:varchar(32)"`
}

func (Knowledge) TableName() string {
	return "knowledge"
}

type KnowledgeDao struct {
	db *gorm.DB
}

func NewKnowledgeDao() *KnowledgeDao {
	return &KnowledgeDao{db: db.GetDB()}
}

func (d *KnowledgeDao) Create(k *Knowledge) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	if k.CreatedAt == "" {
		k.CreatedAt = now
	}
	k.UpdatedAt = now
	return d.db.Create(k).Error
}

func (d *KnowledgeDao) Update(k *Knowledge) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	k.UpdatedAt = time.Now().Format("2006-01-02 15:04:05")
	return d.db.Save(k).Error
}

func (d *KnowledgeDao) Delete(id int64) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	result := d.db.Delete(&Knowledge{}, id)
	if result.Error != nil {
		return result.Error
	}
	return nil
}

func (d *KnowledgeDao) GetByID(id int64) (*Knowledge, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var k Knowledge
	err := d.db.First(&k, id).Error
	if err != nil {
		return nil, err
	}
	return &k, nil
}

func (d *KnowledgeDao) List() ([]*Knowledge, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*Knowledge
	err := d.db.Find(&items).Error
	return items, err
}

func (d *KnowledgeDao) ListByProjectID(projectID int) ([]*Knowledge, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*Knowledge
	err := d.db.Where("project_id = ?", projectID).Find(&items).Error
	return items, err
}
