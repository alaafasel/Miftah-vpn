// Package xraymobile exposes a tiny, stable surface for the Android app:
// Run(configPath), Stop() and Test(configPath).
//
// gomobile bind turns this into `xraymobile.Xraymobile` with static methods,
// which com.miftah.vpn.xray.XrayCore locates by reflection.
package xraymobile

import (
	"encoding/json"
	"errors"
	"os"
	"sync"

	xcore "github.com/xtls/xray-core/core"
	_ "github.com/xtls/xray-core/main/distro/all"
)

var (
	mu       sync.Mutex
	instance *xcore.Instance
)

// Run starts Xray with the JSON config stored at configPath.
func Run(configPath string) error {
	mu.Lock()
	defer mu.Unlock()
	if instance != nil {
		return nil
	}
	cfg, err := load(configPath)
	if err != nil {
		return err
	}
	inst, err := xcore.New(cfg)
	if err != nil {
		return err
	}
	if err := inst.Start(); err != nil {
		return err
	}
	instance = inst
	return nil
}

// Stop shuts down a running instance. Safe to call when not running.
func Stop() error {
	mu.Lock()
	defer mu.Unlock()
	if instance == nil {
		return nil
	}
	err := instance.Close()
	instance = nil
	return err
}

// Test parses and validates the config without starting it.
func Test(configPath string) error {
	_, err := load(configPath)
	return err
}

func load(configPath string) (*xcore.Config, error) {
	if configPath == "" {
		return nil, errors.New("empty config path")
	}
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}
	cfg := new(xcore.Config)
	if err := json.Unmarshal(data, cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}
