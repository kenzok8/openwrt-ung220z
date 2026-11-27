# SPDX-License-Identifier: MIT
#
# Copyright (C) 2026 kenzok8

include $(TOPDIR)/rules.mk

PKG_NAME:=ung220z-tool
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_LICENSE_FILES:=LICENSE

include $(INCLUDE_DIR)/package.mk

define Package/ung220z-tool
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=UNG220Z / ONT credential extraction tool
  URL:=https://github.com/Hut-hzf/ung220z-tool
  DEPENDS:=+python3-light +python3-urllib +openssl-util
  PKGARCH:=all
  MAINTAINER:=kenzok8
endef

define Package/ung220z-tool/description
  One-click credential extraction for UNG220Z and other .gch-based ONTs.
  Opens Telnet via telnet.gch, decrypts the config database (sidbg) and
  extracts Web admin, Telnet, PPPoE and WiFi credentials plus the Linux
  root password hash. Only for your own devices.

  This package vendors upstream Hut-hzf/ung220z-tool (MIT) with small
  OpenWrt/LuCI adaptations, all marked [luci-patch]. See README.md and
  scripts/sync-upstream.sh for re-syncing with upstream.
endef

define Build/Compile
endef

define Package/ung220z-tool/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./files/usr/bin/ung220z $(1)/usr/bin/ung220z
	$(INSTALL_DIR) $(1)/usr/share/doc/ung220z-tool
	$(INSTALL_DATA) ./LICENSE $(1)/usr/share/doc/ung220z-tool/LICENSE
endef

$(eval $(call BuildPackage,ung220z-tool))
