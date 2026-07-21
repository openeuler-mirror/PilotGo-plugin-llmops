package dao

import (
	"errors"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/server/db"
	"gorm.io/gorm"
)

type TopologyConfig struct {
	ID        int64  `json:"id" gorm:"primaryKey"`
	ProjectID int    `json:"project_id" gorm:"not null;index;uniqueIndex:uniq_proj_host_proc"`
	HostID    string `json:"host_id" gorm:"size:255;not null;uniqueIndex:uniq_proj_host_proc"`
	Process   string `json:"process" gorm:"size:255;not null;uniqueIndex:uniq_proj_host_proc"`
	CreatedAt string `json:"created_at" gorm:"type:varchar(32)"`
	UpdatedAt string `json:"updated_at" gorm:"type:varchar(32)"`
}

func (TopologyConfig) TableName() string {
	return "topology_config"
}

type TopologyDao struct {
	db *gorm.DB
}

func NewTopologyDao() *TopologyDao {
	return &TopologyDao{db: db.GetDB()}
}

func (d *TopologyDao) BatchUpdate(items []*TopologyConfig) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	if len(items) == 0 {
		return nil
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	return d.db.Transaction(func(tx *gorm.DB) error {
		for _, c := range items {
			if c == nil {
				return errors.New("nil item in batch")
			}
			if c.ID <= 0 {
				return errors.New("invalid id for update")
			}
			if c.ProjectID <= 0 || c.HostID == "" || c.Process == "" {
				return errors.New("invalid topology config item")
			}
			c.UpdatedAt = now
			if err := tx.Save(c).Error; err != nil {
				return err
			}
		}
		return nil
	})
}

func (d *TopologyDao) Delete(id int64) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	result := d.db.Delete(&TopologyConfig{}, id)
	if result.Error != nil {
		return result.Error
	}
	return nil
}

func (d *TopologyDao) List() ([]*TopologyConfig, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*TopologyConfig
	err := d.db.Find(&items).Error
	return items, err
}

func (d *TopologyDao) ListByProjectID(projectID int) ([]*TopologyConfig, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*TopologyConfig
	err := d.db.Where("project_id = ?", projectID).Find(&items).Error
	return items, err
}

func (d *TopologyDao) BatchInsert(items []*TopologyConfig) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	if len(items) == 0 {
		return nil
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	return d.db.Transaction(func(tx *gorm.DB) error {
		for _, c := range items {
			if c == nil {
				return errors.New("nil item in batch")
			}
			if c.ProjectID <= 0 || c.HostID == "" || c.Process == "" {
				return errors.New("invalid topology config item")
			}
			if c.CreatedAt == "" {
				c.CreatedAt = now
			}
			c.UpdatedAt = now
			if err := tx.Create(c).Error; err != nil {
				return err
			}
		}
		return nil
	})
}
