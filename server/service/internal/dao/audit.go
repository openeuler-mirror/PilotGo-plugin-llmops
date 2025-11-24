package dao

import (
	"errors"
	"time"

	"gitee.com/openeuler/PilotGo-plugin-llmops/server/db"
	"gorm.io/gorm"
)

type Audit struct {
	ID         int64  `json:"id" gorm:"primaryKey"`
	ProjectID  int    `json:"project_id" gorm:"not null;index"`
	Actor      string `json:"actor" gorm:"size:255"`
	Target     string `json:"target" gorm:"size:512"`
	ActionType string `json:"action_type" gorm:"size:255"`
	Action     string `json:"action" gorm:"size:255"`
	Result     string `json:"result" gorm:"size:255"`
	CreatedAt  string `json:"created_at" gorm:"type:varchar(32)"`
	UpdatedAt  string `json:"updated_at" gorm:"type:varchar(32)"`
}

func (Audit) TableName() string {
	return "audit"
}

type AuditDao struct {
	db *gorm.DB
}

func NewAuditDao() *AuditDao {
	return &AuditDao{db: db.GetDB()}
}

func (d *AuditDao) Create(a *Audit) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	now := time.Now().Format("2006-01-02 15:04:05")
	if a.CreatedAt == "" {
		a.CreatedAt = now
	}
	a.UpdatedAt = now
	return d.db.Create(a).Error
}

func (d *AuditDao) Update(a *Audit) error {
	if d.db == nil {
		return errors.New("database not initialized")
	}
	a.UpdatedAt = time.Now().Format("2006-01-02 15:04:05")
	return d.db.Save(a).Error
}

func (d *AuditDao) GetByID(id int64) (*Audit, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var a Audit
	err := d.db.First(&a, id).Error
	if err != nil {
		return nil, err
	}
	return &a, nil
}

func (d *AuditDao) List() ([]*Audit, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*Audit
	err := d.db.Find(&items).Error
	return items, err
}

type AuditQuery struct {
	ProjectID *int
	Actor     string
	Action    string
	Target    string
}

func (d *AuditDao) ListByQuery(q *AuditQuery) ([]*Audit, error) {
	if d.db == nil {
		return nil, errors.New("database not initialized")
	}
	var items []*Audit
	tx := d.db.Model(&Audit{})
	if q != nil {
		if q.ProjectID != nil {
			tx = tx.Where("project_id = ?", *q.ProjectID)
		}
		if q.Actor != "" {
			tx = tx.Where("actor = ?", q.Actor)
		}
		if q.Action != "" {
			tx = tx.Where("action = ?", q.Action)
		}
		if q.Target != "" {
			tx = tx.Where("target = ?", q.Target)
		}
	}
	err := tx.Find(&items).Error
	return items, err
}

func (d *AuditDao) ListByProjectID(projectID int) ([]*Audit, error) {
	return d.ListByQuery(&AuditQuery{ProjectID: &projectID})
}
