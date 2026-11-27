# SPDX-License-Identifier: GPL-3.0-only
#
# Copyright (C) 2026 kenzok8

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-ung220z
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_BUILD_DEPENDS:=luci-base/host

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-ung220z
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=LuCI support for UNG220Z
  DEPENDS:=+ung220z-tool +luci-base +rpcd
  PKGARCH:=all
  URL:=https://github.com/kenzok8/openwrt-ung220z
  MAINTAINER:=kenzok8
endef

define Package/luci-app-ung220z/description
  LuCI web interface for UNG220Z / ONT credential extraction.
  Probe an ONT and extract its Web admin, Telnet, PPPoE and WiFi
  credentials. Only for your own devices.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	po2lmo ./po/zh-cn/ung220z.po $(PKG_BUILD_DIR)/ung220z.zh-cn.lmo
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/luci-app-ung220z/install
	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./root/usr/share/luci/menu.d/luci-app-ung220z.json $(1)/usr/share/luci/menu.d/luci-app-ung220z.json

	$(INSTALL_DIR) $(1)/usr/libexec/rpcd
	$(INSTALL_BIN) ./root/usr/libexec/rpcd/ung220z $(1)/usr/libexec/rpcd/ung220z

	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./root/usr/share/rpcd/acl.d/luci-app-ung220z.json $(1)/usr/share/rpcd/acl.d/luci-app-ung220z.json

	$(INSTALL_DIR) $(1)/www/luci-static/resources/view
	$(INSTALL_DATA) ./htdocs/luci-static/resources/view/ung220z.js $(1)/www/luci-static/resources/view/ung220z.js

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/i18n
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ung220z.zh-cn.lmo $(1)/usr/lib/lua/luci/i18n/ung220z.zh-cn.lmo
endef

define Package/luci-app-ung220z/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || { \
	rm -f /tmp/luci-indexcache.* \
	rm -rf /tmp/luci-modulecache/ \
	/etc/init.d/rpcd reload 2>/dev/null \
	/etc/init.d/uhttpd restart 2>/dev/null \
	exit 0
}
endef

define Package/luci-app-ung220z/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || { \
	rm -rf /tmp/luci-indexcache /tmp/luci-indexcache.* /tmp/luci-modulecache \
	exit 0
}
endef

$(eval $(call BuildPackage,luci-app-ung220z))
