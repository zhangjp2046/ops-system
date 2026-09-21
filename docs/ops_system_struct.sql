CREATE TABLE `alert_rules` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `metric_name` varchar(100) NOT NULL,
  `condition` varchar(10) NOT NULL,
  `threshold` double NOT NULL,
  `severity` varchar(20) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `check_interval` int(11) NOT NULL,
  `notify_enabled` tinyint(1) NOT NULL,
  `notify_channels` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`notify_channels`)),
  `notify_recipients` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`notify_recipients`)),
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_type_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_rules_asset_type_id_73634117_fk_asset_types_id` (`asset_type_id`),
  CONSTRAINT `alert_rules_asset_type_id_73634117_fk_asset_types_id` FOREIGN KEY (`asset_type_id`) REFERENCES `asset_types` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alert_subscriptions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `channel` varchar(20) NOT NULL,
  `config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config`)),
  `severity_filter` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`severity_filter`)),
  `alert_type_filter` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`alert_type_filter`)),
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_subscriptions_customer_id_0f7f3020_fk_customers_id` (`customer_id`),
  CONSTRAINT `alert_subscriptions_customer_id_0f7f3020_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alert_threshold_rules` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `severity` int(11) NOT NULL,
  `operator` varchar(20) NOT NULL,
  `threshold_value` varchar(100) NOT NULL,
  `rule_name` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `sort_order` int(11) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `threshold_id` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alert_threshold_templates` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `protocol` varchar(20) NOT NULL,
  `check_item_code` varchar(50) NOT NULL,
  `check_item_name` varchar(100) NOT NULL,
  `default_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`default_config`)),
  `description` longtext NOT NULL,
  `is_system` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alert_thresholds` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `check_item_code` varchar(50) NOT NULL,
  `check_item_name` varchar(100) NOT NULL,
  `protocol` varchar(20) NOT NULL,
  `threshold_direction` varchar(10) NOT NULL,
  `value_type` varchar(20) NOT NULL,
  `warning_threshold` varchar(100) NOT NULL,
  `error_threshold` varchar(100) NOT NULL,
  `critical_threshold` varchar(100) NOT NULL,
  `unit` varchar(20) NOT NULL,
  `description` longtext NOT NULL,
  `config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config`)),
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_type_id` bigint(20) DEFAULT NULL,
  `created_by_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  `is_monitoring_item` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `alert_thresholds_customer_id_asset_type_i_75b8fd4e_uniq` (`customer_id`,`asset_type_id`,`check_item_code`),
  KEY `alert_thres_custome_5d06e1_idx` (`customer_id`,`is_active`),
  KEY `alert_thres_protoco_f5e8cd_idx` (`protocol`),
  KEY `alert_thres_check_i_90ab52_idx` (`check_item_code`),
  KEY `alert_thresholds_is_monitoring_item_6d8a817c` (`is_monitoring_item`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alerts` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `message` longtext NOT NULL,
  `severity` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `trigger_value` double DEFAULT NULL,
  `threshold` double DEFAULT NULL,
  `occurred_at` datetime(6) NOT NULL,
  `acknowledged_at` datetime(6) DEFAULT NULL,
  `resolved_at` datetime(6) DEFAULT NULL,
  `acknowledged_by` varchar(100) NOT NULL,
  `resolved_by` varchar(100) NOT NULL,
  `resolution_note` longtext NOT NULL,
  `alert_rule_id` bigint(20) DEFAULT NULL,
  `asset_id` bigint(20) NOT NULL,
  `monitoring_result_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `alerts_asset_i_a5ee48_idx` (`asset_id`,`status`),
  KEY `alerts_severit_ae6d4c_idx` (`severity`,`status`),
  KEY `alerts_occurre_73f3e4_idx` (`occurred_at`),
  KEY `alerts_alert_rule_id_68b77ba6_fk_alert_rules_id` (`alert_rule_id`),
  KEY `alerts_monitoring_result_id_c8e30df2_fk_monitoring_results_id` (`monitoring_result_id`),
  CONSTRAINT `alerts_alert_rule_id_68b77ba6_fk_alert_rules_id` FOREIGN KEY (`alert_rule_id`) REFERENCES `alert_rules` (`id`),
  CONSTRAINT `alerts_asset_id_40b85b1b_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `alerts_monitoring_result_id_c8e30df2_fk_monitoring_results_id` FOREIGN KEY (`monitoring_result_id`) REFERENCES `monitoring_results` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alerts_alert` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `severity` int(11) NOT NULL,
  `alert_type` varchar(50) NOT NULL,
  `source` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `alert_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`alert_data`)),
  `metric_name` varchar(100) NOT NULL,
  `metric_value` varchar(100) NOT NULL,
  `threshold` varchar(100) NOT NULL,
  `occurred_at` datetime(6) DEFAULT NULL,
  `acknowledged_at` datetime(6) DEFAULT NULL,
  `resolved_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `alerts_aler_custome_41279c_idx` (`customer_id`,`status`),
  KEY `alerts_aler_created_8af5ce_idx` (`created_at`),
  KEY `alerts_alert_asset_id_7f8b2d3d_fk_assets_id` (`asset_id`),
  CONSTRAINT `alerts_alert_asset_id_7f8b2d3d_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `alerts_alert_customer_id_208acb30_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=219 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `alerts_alert_rules` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `status` varchar(20) NOT NULL,
  `severity` int(11) NOT NULL,
  `conditions` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`conditions`)),
  `auto_create_workorder` tinyint(1) NOT NULL,
  `workorder_template` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`workorder_template`)),
  `notify_enabled` tinyint(1) NOT NULL,
  `notify_channels` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`notify_channels`)),
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `alerts_alert_rules_customer_id_f0f007e5_fk_customers_id` (`customer_id`),
  CONSTRAINT `alerts_alert_rules_customer_id_f0f007e5_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `asset_data` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `string_value` longtext NOT NULL,
  `number_value` decimal(20,6) DEFAULT NULL,
  `boolean_value` tinyint(1) DEFAULT NULL,
  `date_value` date DEFAULT NULL,
  `datetime_value` datetime(6) DEFAULT NULL,
  `json_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`json_value`)),
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  `field_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `asset_data_asset_id_field_id_3545dd66_uniq` (`asset_id`,`field_id`),
  KEY `asset_data_asset_i_11afb4_idx` (`asset_id`),
  KEY `asset_data_field_i_e89921_idx` (`field_id`),
  CONSTRAINT `asset_data_asset_id_543eccd0_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `asset_data_field_id_81c3dd35_fk_asset_fields_id` FOREIGN KEY (`field_id`) REFERENCES `asset_fields` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `asset_fields` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `field_code` varchar(50) NOT NULL,
  `field_name` varchar(100) NOT NULL,
  `field_type` varchar(20) NOT NULL,
  `is_required` tinyint(1) NOT NULL,
  `is_unique` tinyint(1) NOT NULL,
  `is_searchable` tinyint(1) NOT NULL,
  `is_filterable` tinyint(1) NOT NULL,
  `field_label` varchar(100) NOT NULL,
  `placeholder` varchar(200) NOT NULL,
  `help_text` longtext NOT NULL,
  `sort_order` int(11) NOT NULL,
  `validation_rules` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`validation_rules`)),
  `default_value` longtext NOT NULL,
  `options` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`options`)),
  `asset_type_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `asset_fields_asset_type_id_field_code_143ca665_uniq` (`asset_type_id`,`field_code`),
  CONSTRAINT `asset_fields_asset_type_id_55b3c180_fk_asset_types_id` FOREIGN KEY (`asset_type_id`) REFERENCES `asset_types` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `asset_status_history` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `changed_by` varchar(100) NOT NULL,
  `change_reason` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `asset_statu_asset_i_07441f_idx` (`asset_id`,`created_at`),
  CONSTRAINT `asset_status_history_asset_id_90fb1ae0_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `asset_types` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `type_code` varchar(50) NOT NULL,
  `type_name` varchar(100) NOT NULL,
  `plugin_id` varchar(100) NOT NULL,
  `icon` varchar(50) NOT NULL,
  `color` varchar(20) NOT NULL,
  `description` longtext NOT NULL,
  `sort_order` int(11) NOT NULL,
  `is_system` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  `parent_type_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `asset_types_customer_id_type_code_6a7cec25_uniq` (`customer_id`,`type_code`),
  KEY `asset_types_parent_type_id_1ad3c469_fk_asset_types_id` (`parent_type_id`),
  CONSTRAINT `asset_types_customer_id_302dc9a9_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `asset_types_parent_type_id_1ad3c469_fk_asset_types_id` FOREIGN KEY (`parent_type_id`) REFERENCES `asset_types` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `assets` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `asset_code` varchar(100) NOT NULL,
  `asset_name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `location` varchar(200) NOT NULL,
  `room` varchar(100) NOT NULL,
  `rack` varchar(100) NOT NULL,
  `position` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL,
  `importance_level` varchar(20) NOT NULL,
  `purchase_date` date DEFAULT NULL,
  `warranty_end` date DEFAULT NULL,
  `decommission_date` date DEFAULT NULL,
  `owner` varchar(100) NOT NULL,
  `department` varchar(100) NOT NULL,
  `vendor` varchar(100) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_type_id` bigint(20) NOT NULL,
  `created_by_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) NOT NULL,
  `updated_by_id` bigint(20) DEFAULT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `last_check_time` datetime(6) DEFAULT NULL,
  `online` tinyint(1) NOT NULL,
  `database` varchar(100) NOT NULL,
  `db_type` varchar(20) NOT NULL,
  `password` varchar(200) NOT NULL,
  `port` varchar(10) NOT NULL,
  `protocol` varchar(20) NOT NULL,
  `username` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assets_customer_id_asset_code_cf5aff67_uniq` (`customer_id`,`asset_code`),
  KEY `assets_created_by_id_1d6b23a3_fk_users_id` (`created_by_id`),
  KEY `assets_updated_by_id_db71c8f3_fk_users_id` (`updated_by_id`),
  KEY `assets_asset_c_4e968f_idx` (`asset_code`),
  KEY `assets_status_326766_idx` (`status`),
  KEY `assets_asset_t_57ae73_idx` (`asset_type_id`),
  KEY `assets_custome_cdfca9_idx` (`customer_id`,`status`),
  KEY `assets_online_e2a7af64` (`online`),
  CONSTRAINT `assets_asset_type_id_21c80ec7_fk_asset_types_id` FOREIGN KEY (`asset_type_id`) REFERENCES `asset_types` (`id`),
  CONSTRAINT `assets_created_by_id_1d6b23a3_fk_users_id` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  CONSTRAINT `assets_customer_id_13da8a71_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `assets_updated_by_id_db71c8f3_fk_users_id` FOREIGN KEY (`updated_by_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=201 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=201 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `customers` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `customer_code` varchar(50) NOT NULL,
  `customer_name` varchar(100) NOT NULL,
  `customer_type` varchar(50) NOT NULL,
  `industry` varchar(50) NOT NULL,
  `contact_person` varchar(50) NOT NULL,
  `contact_phone` varchar(20) NOT NULL,
  `contact_email` varchar(100) NOT NULL,
  `address` longtext NOT NULL,
  `config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config`)),
  `plugins` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`plugins`)),
  `status` varchar(20) NOT NULL,
  `contract_start` date DEFAULT NULL,
  `contract_end` date DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint(20) DEFAULT NULL,
  `updated_by_id` bigint(20) DEFAULT NULL,
  `api_key` varchar(64) DEFAULT NULL,
  `api_secret` varchar(128) DEFAULT NULL,
  `is_local_deployment` tinyint(1) NOT NULL,
  `local_endpoint` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `customer_code` (`customer_code`),
  UNIQUE KEY `api_key` (`api_key`),
  KEY `customers_created_by_id_3d0160f2_fk_users_id` (`created_by_id`),
  KEY `customers_updated_by_id_62864352_fk_users_id` (`updated_by_id`),
  CONSTRAINT `customers_created_by_id_3d0160f2_fk_users_id` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  CONSTRAINT `customers_updated_by_id_62864352_fk_users_id` FOREIGN KEY (`updated_by_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `discovered_devices` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `ip_address` char(39) NOT NULL,
  `mac_address` varchar(17) NOT NULL,
  `hostname` varchar(200) NOT NULL,
  `device_type` varchar(20) NOT NULL,
  `os_type` varchar(20) NOT NULL,
  `vendor` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  `open_ports` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`open_ports`)),
  `response_time` double DEFAULT NULL,
  `snmp_sysDescr` longtext NOT NULL,
  `snmp_sysName` varchar(200) NOT NULL,
  `snmp_sysLocation` varchar(200) NOT NULL,
  `ssh_banner` longtext NOT NULL,
  `http_title` varchar(200) NOT NULL,
  `is_online` tinyint(1) NOT NULL,
  `raw_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`raw_data`)),
  `is_imported` tinyint(1) NOT NULL,
  `discovered_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  `imported_asset_id` bigint(20) DEFAULT NULL,
  `task_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `discovered_devices_task_id_1b7752a2_fk_discovery_tasks_id` (`task_id`),
  KEY `discovered__ip_addr_2afbb4_idx` (`ip_address`),
  KEY `discovered__custome_ac9b42_idx` (`customer_id`,`ip_address`),
  KEY `discovered_devices_imported_asset_id_4c12faac_fk_assets_id` (`imported_asset_id`),
  CONSTRAINT `discovered_devices_customer_id_d10270f6_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `discovered_devices_imported_asset_id_4c12faac_fk_assets_id` FOREIGN KEY (`imported_asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `discovered_devices_task_id_1b7752a2_fk_discovery_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `discovery_tasks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `discovery_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `scan_type` varchar(20) NOT NULL,
  `target_ranges` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`target_ranges`)),
  `ports` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`ports`)),
  `timeout` int(11) NOT NULL,
  `snmp_community` varchar(100) NOT NULL,
  `status` varchar(20) NOT NULL,
  `total_ips` int(11) NOT NULL,
  `scanned_ips` int(11) NOT NULL,
  `found_devices` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `created_by` varchar(100) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `discovery_tasks_customer_id_7929e579_fk_customers_id` (`customer_id`),
  CONSTRAINT `discovery_tasks_customer_id_7929e579_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_users_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspection_items` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `item_code` varchar(50) NOT NULL,
  `item_name` varchar(100) NOT NULL,
  `category` varchar(50) NOT NULL,
  `result` varchar(10) NOT NULL,
  `severity` varchar(20) NOT NULL,
  `actual_value` varchar(500) NOT NULL,
  `expected_value` varchar(500) NOT NULL,
  `message` longtext NOT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`details`)),
  `inspection_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `inspection_items_inspection_id_07141610_fk_inspections_id` (`inspection_id`),
  CONSTRAINT `inspection_items_inspection_id_07141610_fk_inspections_id` FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2185 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspection_plans` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `code` varchar(50) NOT NULL,
  `description` longtext NOT NULL,
  `cycle` varchar(20) NOT NULL,
  `scheduled_time` time(6) NOT NULL,
  `is_auto_execute` tinyint(1) NOT NULL,
  `status` varchar(20) NOT NULL,
  `check_items` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`check_items`)),
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  `protocol` varchar(20) NOT NULL,
  `asset_count` int(11) NOT NULL DEFAULT 0,
  `asset_type_ids` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '[]' CHECK (json_valid(`asset_type_ids`)),
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `inspection_plans_customer_id_d404aff0_fk_customers_id` (`customer_id`),
  CONSTRAINT `inspection_plans_customer_id_d404aff0_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspection_records` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `total_checks` int(11) NOT NULL,
  `pass_checks` int(11) NOT NULL,
  `warning_checks` int(11) NOT NULL,
  `fail_checks` int(11) NOT NULL,
  `skip_checks` int(11) NOT NULL,
  `status` varchar(20) NOT NULL,
  `overall_status` varchar(20) NOT NULL,
  `summary` longtext NOT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  `executor_id` bigint(20) DEFAULT NULL,
  `task_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `task_id` (`task_id`),
  KEY `inspection_records_asset_id_5be6f18a_fk_assets_id` (`asset_id`),
  KEY `inspection_records_executor_id_3e98aa11_fk_users_id` (`executor_id`),
  CONSTRAINT `inspection_records_asset_id_5be6f18a_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `inspection_records_executor_id_3e98aa11_fk_users_id` FOREIGN KEY (`executor_id`) REFERENCES `users` (`id`),
  CONSTRAINT `inspection_records_task_id_e2b7cc95_fk_inspection_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `inspection_tasks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=398 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspection_results` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `check_item` varchar(100) NOT NULL,
  `check_item_code` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL,
  `result_value` varchar(500) NOT NULL,
  `result_message` longtext NOT NULL,
  `expected_value` varchar(200) NOT NULL,
  `threshold_min` varchar(100) NOT NULL,
  `threshold_max` varchar(100) NOT NULL,
  `suggestion` longtext NOT NULL,
  `executed_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  `task_id` bigint(20) NOT NULL,
  `severity` int(11) DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `inspection_results_task_id_96694d7b_fk_inspection_tasks_id` (`task_id`),
  KEY `inspection_results_asset_id_a25afb7b_fk_assets_id` (`asset_id`),
  CONSTRAINT `inspection_results_asset_id_a25afb7b_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `inspection_results_task_id_96694d7b_fk_inspection_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `inspection_tasks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3050 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspection_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `scheduled_time` datetime(6) NOT NULL,
  `executed_time` datetime(6) DEFAULT NULL,
  `priority` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  `executor_id` bigint(20) DEFAULT NULL,
  `plan_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `inspection_tasks_asset_id_b60deef0_fk_assets_id` (`asset_id`),
  KEY `inspection_tasks_executor_id_5969ee82_fk_users_id` (`executor_id`),
  KEY `inspection_tasks_plan_id_b0583f9a_fk_inspection_plans_id` (`plan_id`),
  CONSTRAINT `inspection_tasks_asset_id_b60deef0_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `inspection_tasks_executor_id_5969ee82_fk_users_id` FOREIGN KEY (`executor_id`) REFERENCES `users` (`id`),
  CONSTRAINT `inspection_tasks_plan_id_b0583f9a_fk_inspection_plans_id` FOREIGN KEY (`plan_id`) REFERENCES `inspection_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=201 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspection_templates` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `inspection_type` varchar(50) NOT NULL,
  `asset_type` varchar(50) NOT NULL,
  `items` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`items`)),
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `inspections` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `inspection_type` varchar(50) NOT NULL,
  `asset_type` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `total_items` int(11) NOT NULL,
  `passed_items` int(11) NOT NULL,
  `warning_items` int(11) NOT NULL,
  `failed_items` int(11) NOT NULL,
  `duration_ms` int(11) NOT NULL,
  `summary` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `inspections_asset_id_391a3442_fk_assets_id` (`asset_id`),
  KEY `inspections_customer_id_9dac741d_fk_customers_id` (`customer_id`),
  CONSTRAINT `inspections_asset_id_391a3442_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `inspections_customer_id_9dac741d_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=445 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `monitor_test_config` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `protocol` varchar(20) NOT NULL,
  `host` varchar(200) NOT NULL,
  `port` int(11) DEFAULT NULL,
  `config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config`)),
  `interval` int(11) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `last_test_status` varchar(20) NOT NULL,
  `last_test_time` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) DEFAULT NULL,
  `created_by_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `monitor_test_config_asset_id_db8f2180_fk_assets_id` (`asset_id`),
  KEY `monitor_test_config_created_by_id_77a66bfe_fk_users_id` (`created_by_id`),
  KEY `monitor_test_config_customer_id_e34736e5_fk_customers_id` (`customer_id`),
  CONSTRAINT `monitor_test_config_asset_id_db8f2180_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `monitor_test_config_created_by_id_77a66bfe_fk_users_id` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  CONSTRAINT `monitor_test_config_customer_id_e34736e5_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `monitor_test_result` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `response_time` double DEFAULT NULL,
  `error_message` longtext NOT NULL,
  `data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`data`)),
  `test_duration` double DEFAULT NULL,
  `remote_addr` char(39) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `config_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `monitor_tes_config__71fa0f_idx` (`config_id`,`created_at`),
  CONSTRAINT `monitor_test_result_config_id_122e916a_fk_monitor_test_config_id` FOREIGN KEY (`config_id`) REFERENCES `monitor_test_config` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=55 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `monitoring_data_points` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `check_item_code` varchar(50) NOT NULL,
  `check_item_name` varchar(100) NOT NULL,
  `protocol` varchar(20) NOT NULL,
  `numeric_value` double DEFAULT NULL,
  `display_value` varchar(200) NOT NULL,
  `severity` int(11) NOT NULL,
  `warning_threshold` varchar(50) NOT NULL,
  `error_threshold` varchar(50) NOT NULL,
  `result_message` longtext NOT NULL,
  `suggestion` longtext NOT NULL,
  `recorded_at` datetime(6) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  `inspection_task_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `monitoring__asset_i_9ce2e0_idx` (`asset_id`,`check_item_code`,`recorded_at`),
  KEY `monitoring__asset_i_d3fe95_idx` (`asset_id`,`protocol`,`recorded_at`),
  KEY `monitoring__custome_aca01e_idx` (`customer_id`,`recorded_at`),
  KEY `monitoring__check_i_172551_idx` (`check_item_code`,`recorded_at`),
  KEY `monitoring_data_poin_inspection_task_id_833b5d56_fk_inspectio` (`inspection_task_id`),
  KEY `monitoring_data_points_check_item_code_cbf4ab86` (`check_item_code`),
  KEY `monitoring_data_points_protocol_00dd92ac` (`protocol`),
  KEY `monitoring_data_points_recorded_at_7e2f6c94` (`recorded_at`),
  CONSTRAINT `monitoring_data_poin_inspection_task_id_833b5d56_fk_inspectio` FOREIGN KEY (`inspection_task_id`) REFERENCES `inspection_tasks` (`id`),
  CONSTRAINT `monitoring_data_points_asset_id_8f8f58a7_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `monitoring_data_points_customer_id_0911b66f_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=148 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `monitoring_results` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `response_time` double DEFAULT NULL,
  `uptime` double DEFAULT NULL,
  `cpu_usage` double DEFAULT NULL,
  `memory_usage` double DEFAULT NULL,
  `disk_usage` double DEFAULT NULL,
  `network_in` double DEFAULT NULL,
  `network_out` double DEFAULT NULL,
  `port_check` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`port_check`)),
  `error_message` longtext NOT NULL,
  `error_details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`error_details`)),
  `raw_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`raw_data`)),
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  `asset_id` bigint(20) NOT NULL,
  `task_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `monitoring__asset_i_e43b85_idx` (`asset_id`,`status`),
  KEY `monitoring__start_t_0fb730_idx` (`start_time`),
  KEY `monitoring_results_task_id_9dde8bde_fk_monitoring_tasks_id` (`task_id`),
  CONSTRAINT `monitoring_results_asset_id_a698400a_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `monitoring_results_task_id_9dde8bde_fk_monitoring_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `monitoring_tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `monitoring_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `task_type` varchar(20) NOT NULL,
  `config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config`)),
  `interval` int(11) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `is_critical` tinyint(1) NOT NULL,
  `status` varchar(20) NOT NULL,
  `last_run_time` datetime(6) DEFAULT NULL,
  `next_run_time` datetime(6) DEFAULT NULL,
  `success_count` int(11) NOT NULL,
  `failure_count` int(11) NOT NULL,
  `last_success_time` datetime(6) DEFAULT NULL,
  `last_failure_time` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `monitoring_tasks_asset_id_c832e295_fk_assets_id` (`asset_id`),
  CONSTRAINT `monitoring_tasks_asset_id_c832e295_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `push_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `push_type` varchar(20) NOT NULL,
  `status` varchar(10) NOT NULL,
  `records_count` int(11) NOT NULL,
  `error_message` longtext NOT NULL,
  `endpoint` varchar(200) NOT NULL,
  `request_data_size` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `last_retry_at` datetime(6) DEFAULT NULL,
  `next_retry_at` datetime(6) DEFAULT NULL,
  `request_payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`request_payload`)),
  `retry_count` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `push_logs_push_type_be0eb45a` (`push_type`),
  KEY `push_logs_created_at_0e6adc9b` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=1455 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduled_task_executions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `result_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`result_data`)),
  `error_message` longtext NOT NULL,
  `output` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `task_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduled_task_executions_task_id_d3d94f0b_fk_scheduled_tasks_id` (`task_id`),
  CONSTRAINT `scheduled_task_executions_task_id_d3d94f0b_fk_scheduled_tasks_id` FOREIGN KEY (`task_id`) REFERENCES `scheduled_tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduled_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `task_type` varchar(50) NOT NULL,
  `target_type` varchar(50) NOT NULL,
  `target_id` bigint(20) DEFAULT NULL,
  `config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config`)),
  `cron_expression` varchar(100) NOT NULL,
  `interval_seconds` int(11) DEFAULT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `is_running` tinyint(1) NOT NULL,
  `last_run_time` datetime(6) DEFAULT NULL,
  `next_run_time` datetime(6) DEFAULT NULL,
  `last_status` varchar(20) DEFAULT NULL,
  `last_result` longtext NOT NULL,
  `success_count` int(11) NOT NULL,
  `failure_count` int(11) NOT NULL,
  `total_runs` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_adhoc_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `task_type` varchar(20) NOT NULL,
  `task_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`task_config`)),
  `priority` varchar(10) NOT NULL,
  `status` varchar(10) NOT NULL,
  `scheduled_at` datetime(6) DEFAULT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `ended_at` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `retry_count` int(11) NOT NULL,
  `max_retries` int(11) NOT NULL,
  `result_summary` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`result_summary`)),
  `error_message` longtext NOT NULL,
  `created_by` varchar(100) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_adhoc_tasks_customer_id_fa58ee02_fk_customers_id` (`customer_id`),
  CONSTRAINT `scheduler_adhoc_tasks_customer_id_fa58ee02_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_plan_executions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(10) NOT NULL,
  `trigger` varchar(20) NOT NULL,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `total_tasks` int(11) NOT NULL,
  `success_tasks` int(11) NOT NULL,
  `failed_tasks` int(11) NOT NULL,
  `skipped_tasks` int(11) NOT NULL,
  `error_message` longtext NOT NULL,
  `plan_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_plan_executions_plan_id_c2826880_fk_scheduler_plans_id` (`plan_id`),
  CONSTRAINT `scheduler_plan_executions_plan_id_c2826880_fk_scheduler_plans_id` FOREIGN KEY (`plan_id`) REFERENCES `scheduler_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_plan_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `task_type` varchar(20) NOT NULL,
  `execution_order` int(11) NOT NULL,
  `execution_mode` varchar(10) NOT NULL,
  `task_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`task_config`)),
  `timeout_seconds` int(11) NOT NULL,
  `depends_on` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`depends_on`)),
  `skip_on_failure` tinyint(1) NOT NULL,
  `max_retries` int(11) NOT NULL,
  `retry_interval_seconds` int(11) NOT NULL,
  `notify_on_success` tinyint(1) NOT NULL,
  `notify_on_failure` tinyint(1) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `plan_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_plan_tasks_plan_id_25ec3230_fk_scheduler_plans_id` (`plan_id`),
  CONSTRAINT `scheduler_plan_tasks_plan_id_25ec3230_fk_scheduler_plans_id` FOREIGN KEY (`plan_id`) REFERENCES `scheduler_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_plans` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `plan_type` varchar(20) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `cron_expression` varchar(100) NOT NULL,
  `interval_seconds` int(11) DEFAULT NULL,
  `next_run_time` datetime(6) DEFAULT NULL,
  `last_run_time` datetime(6) DEFAULT NULL,
  `notify_on_success` tinyint(1) NOT NULL,
  `notify_on_failure` tinyint(1) NOT NULL,
  `notify_channels` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`notify_channels`)),
  `conflict_strategy` varchar(10) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  `inspection_plan_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_plans_customer_id_339c0b28_fk_customers_id` (`customer_id`),
  KEY `scheduler_plans_inspection_plan_id_14a361d1_fk_inspectio` (`inspection_plan_id`),
  CONSTRAINT `scheduler_plans_customer_id_339c0b28_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `scheduler_plans_inspection_plan_id_14a361d1_fk_inspectio` FOREIGN KEY (`inspection_plan_id`) REFERENCES `inspection_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_task_instances` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(10) NOT NULL,
  `start_time` datetime(6) DEFAULT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `retry_count` int(11) NOT NULL,
  `result_summary` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`result_summary`)),
  `error_message` longtext NOT NULL,
  `output` longtext NOT NULL,
  `plan_execution_id` bigint(20) NOT NULL,
  `plan_task_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_task_insta_plan_execution_id_8ac483ca_fk_scheduler` (`plan_execution_id`),
  KEY `scheduler_task_insta_plan_task_id_442a4950_fk_scheduler` (`plan_task_id`),
  CONSTRAINT `scheduler_task_insta_plan_execution_id_8ac483ca_fk_scheduler` FOREIGN KEY (`plan_execution_id`) REFERENCES `scheduler_plan_executions` (`id`),
  CONSTRAINT `scheduler_task_insta_plan_task_id_442a4950_fk_scheduler` FOREIGN KEY (`plan_task_id`) REFERENCES `scheduler_plan_tasks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_task_locks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `lock_key` varchar(200) NOT NULL,
  `execution_id` varchar(100) NOT NULL,
  `locked_at` datetime(6) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lock_key` (`lock_key`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_task_templates` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `category` varchar(20) NOT NULL,
  `icon` varchar(50) NOT NULL,
  `color` varchar(20) NOT NULL,
  `task_type` varchar(20) NOT NULL,
  `config_schema` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config_schema`)),
  `default_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`default_config`)),
  `config_ui_hints` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config_ui_hints`)),
  `is_builtin` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `usage_count` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_v2_adhoc_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `task_type` varchar(50) NOT NULL,
  `task_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`task_config`)),
  `status` varchar(20) NOT NULL,
  `triggered_by` varchar(100) NOT NULL,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `result_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`result_data`)),
  `error_message` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_v2_plan_executions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `trigger` varchar(20) NOT NULL,
  `total_tasks` int(11) NOT NULL,
  `completed_tasks` int(11) NOT NULL,
  `success_tasks` int(11) NOT NULL,
  `failed_tasks` int(11) NOT NULL,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `result_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`result_data`)),
  `error_message` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `plan_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_v2_plan_ex_plan_id_f1137dcd_fk_scheduler` (`plan_id`),
  CONSTRAINT `scheduler_v2_plan_ex_plan_id_f1137dcd_fk_scheduler` FOREIGN KEY (`plan_id`) REFERENCES `scheduler_v2_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_v2_plan_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `task_type` varchar(50) NOT NULL,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `task_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`task_config`)),
  `is_enabled` tinyint(1) NOT NULL,
  `execution_order` int(11) NOT NULL,
  `timeout_seconds` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `plan_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_v2_plan_ta_plan_id_208c9739_fk_scheduler` (`plan_id`),
  CONSTRAINT `scheduler_v2_plan_ta_plan_id_208c9739_fk_scheduler` FOREIGN KEY (`plan_id`) REFERENCES `scheduler_v2_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_v2_plans` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `plan_type` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL,
  `inspection_plan_name` varchar(200) NOT NULL,
  `trigger_mode` varchar(20) NOT NULL,
  `cron_expression` varchar(100) NOT NULL,
  `interval_seconds` int(11) DEFAULT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `max_concurrent` int(11) NOT NULL,
  `timeout_seconds` int(11) NOT NULL,
  `next_run_time` datetime(6) DEFAULT NULL,
  `last_run_time` datetime(6) DEFAULT NULL,
  `total_executions` int(11) NOT NULL,
  `success_count` int(11) NOT NULL,
  `failure_count` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `inspection_plan_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_v2_plans_inspection_plan_id_c2b4c905_fk_inspectio` (`inspection_plan_id`),
  CONSTRAINT `scheduler_v2_plans_inspection_plan_id_c2b4c905_fk_inspectio` FOREIGN KEY (`inspection_plan_id`) REFERENCES `inspection_plans` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_v2_task_instances` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `start_time` datetime(6) DEFAULT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `result_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`result_data`)),
  `error_message` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `plan_execution_id` bigint(20) NOT NULL,
  `plan_task_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `scheduler_v2_task_in_plan_execution_id_dac1967b_fk_scheduler` (`plan_execution_id`),
  KEY `scheduler_v2_task_in_plan_task_id_6d65cff6_fk_scheduler` (`plan_task_id`),
  CONSTRAINT `scheduler_v2_task_in_plan_execution_id_dac1967b_fk_scheduler` FOREIGN KEY (`plan_execution_id`) REFERENCES `scheduler_v2_plan_executions` (`id`),
  CONSTRAINT `scheduler_v2_task_in_plan_task_id_6d65cff6_fk_scheduler` FOREIGN KEY (`plan_task_id`) REFERENCES `scheduler_v2_plan_tasks` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `scheduler_v2_task_templates` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `category` varchar(50) NOT NULL,
  `icon` varchar(50) NOT NULL,
  `color` varchar(20) NOT NULL,
  `task_type` varchar(50) NOT NULL,
  `default_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`default_config`)),
  `usage_count` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `system_settings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `key` varchar(100) NOT NULL,
  `value` longtext NOT NULL,
  `category` varchar(50) NOT NULL,
  `label` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `field_type` varchar(20) NOT NULL,
  `options` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`options`)),
  `is_sensitive` tinyint(1) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `updated_by` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key` (`key`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `topology_edges` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `edge_type` varchar(20) NOT NULL,
  `bandwidth` varchar(50) NOT NULL,
  `latency` int(11) DEFAULT NULL,
  `source_port` varchar(50) NOT NULL,
  `target_port` varchar(50) NOT NULL,
  `description` varchar(200) NOT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`metadata`)),
  `created_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  `source_id` bigint(20) NOT NULL,
  `target_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `topology_edges_customer_id_e2c72410_fk_customers_id` (`customer_id`),
  KEY `topology_edges_source_id_517a7622_fk_topology_nodes_id` (`source_id`),
  KEY `topology_edges_target_id_b5b2a2e7_fk_topology_nodes_id` (`target_id`),
  CONSTRAINT `topology_edges_customer_id_e2c72410_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `topology_edges_source_id_517a7622_fk_topology_nodes_id` FOREIGN KEY (`source_id`) REFERENCES `topology_nodes` (`id`),
  CONSTRAINT `topology_edges_target_id_b5b2a2e7_fk_topology_nodes_id` FOREIGN KEY (`target_id`) REFERENCES `topology_nodes` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `topology_nodes` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `node_type` varchar(20) NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `mac_address` varchar(17) NOT NULL,
  `location` varchar(200) NOT NULL,
  `device_type` varchar(20) NOT NULL,
  `is_online` tinyint(1) NOT NULL,
  `x_position` double DEFAULT NULL,
  `y_position` double DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`metadata`)),
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `asset_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) NOT NULL,
  `discovered_device_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `topology_nodes_asset_id_ec035509_fk_assets_id` (`asset_id`),
  KEY `topology_nodes_customer_id_f1c27a4b_fk_customers_id` (`customer_id`),
  KEY `topology_nodes_discovered_device_id_d19943ba_fk_discovere` (`discovered_device_id`),
  CONSTRAINT `topology_nodes_asset_id_ec035509_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `topology_nodes_customer_id_f1c27a4b_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `topology_nodes_discovered_device_id_d19943ba_fk_discovere` FOREIGN KEY (`discovered_device_id`) REFERENCES `discovered_devices` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `users` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `full_name` varchar(100) NOT NULL,
  `phone` varchar(20) NOT NULL,
  `avatar_url` varchar(500) NOT NULL,
  `role` varchar(50) NOT NULL,
  `permissions` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`permissions`)),
  `is_active` tinyint(1) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `last_login_time` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `users_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_groups_user_id_group_id_fc7788e8_uniq` (`user_id`,`group_id`),
  KEY `users_groups_group_id_2f3517aa_fk_auth_group_id` (`group_id`),
  CONSTRAINT `users_groups_group_id_2f3517aa_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `users_groups_user_id_f500bee5_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `users_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_user_permissions_user_id_permission_id_3b86cbdf_uniq` (`user_id`,`permission_id`),
  KEY `users_user_permissio_permission_id_6d08dcd2_fk_auth_perm` (`permission_id`),
  CONSTRAINT `users_user_permissio_permission_id_6d08dcd2_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `users_user_permissions_user_id_92473840_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `work_order_comments` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `content` longtext NOT NULL,
  `cttime` datetime(6) NOT NULL,
  `order_id` bigint(20) NOT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `work_order_comments_order_id_bae97cfa_fk_work_orders_id` (`order_id`),
  KEY `work_order_comments_user_id_4d0c79ad_fk_users_id` (`user_id`),
  CONSTRAINT `work_order_comments_order_id_bae97cfa_fk_work_orders_id` FOREIGN KEY (`order_id`) REFERENCES `work_orders` (`id`),
  CONSTRAINT `work_order_comments_user_id_4d0c79ad_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `work_order_steps` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` int(11) NOT NULL,
  `step_type` varchar(50) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `attachment` varchar(500) NOT NULL,
  `flow_time` datetime(6) DEFAULT NULL,
  `cttime` datetime(6) NOT NULL,
  `handler_id` bigint(20) DEFAULT NULL,
  `order_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `work_order_steps_handler_id_165e54e1_fk_users_id` (`handler_id`),
  KEY `work_order_steps_order_id_7d1c1bab_fk_work_orders_id` (`order_id`),
  CONSTRAINT `work_order_steps_handler_id_165e54e1_fk_users_id` FOREIGN KEY (`handler_id`) REFERENCES `users` (`id`),
  CONSTRAINT `work_order_steps_order_id_7d1c1bab_fk_work_orders_id` FOREIGN KEY (`order_id`) REFERENCES `work_orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE `work_orders` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `resume` varchar(500) DEFAULT NULL,
  `contact_name` varchar(50) NOT NULL,
  `contact_phone` varchar(20) NOT NULL,
  `order_type` int(11) DEFAULT NULL,
  `priority` int(11) NOT NULL,
  `status` int(11) NOT NULL,
  `occdate` datetime(6) DEFAULT NULL,
  `cttime` datetime(6) NOT NULL,
  `updatetime` datetime(6) NOT NULL,
  `description` longtext NOT NULL,
  `asset_id` bigint(20) DEFAULT NULL,
  `creator_id` bigint(20) DEFAULT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  `handler_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `work_orders_asset_id_92971948_fk_assets_id` (`asset_id`),
  KEY `work_orders_creator_id_bcba1c93_fk_users_id` (`creator_id`),
  KEY `work_orders_customer_id_0248d41e_fk_customers_id` (`customer_id`),
  KEY `work_orders_handler_id_3457c553_fk_users_id` (`handler_id`),
  CONSTRAINT `work_orders_asset_id_92971948_fk_assets_id` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`),
  CONSTRAINT `work_orders_creator_id_bcba1c93_fk_users_id` FOREIGN KEY (`creator_id`) REFERENCES `users` (`id`),
  CONSTRAINT `work_orders_customer_id_0248d41e_fk_customers_id` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  CONSTRAINT `work_orders_handler_id_3457c553_fk_users_id` FOREIGN KEY (`handler_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

