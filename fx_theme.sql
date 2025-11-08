/*
 Navicat Premium Dump SQL

 Source Server         : faxuan
 Source Server Type    : MySQL
 Source Server Version : 80043 (8.0.43)
 Source Host           : localhost:3306
 Source Schema         : faxuan2

 Target Server Type    : MySQL
 Target Server Version : 80043 (8.0.43)
 File Encoding         : 65001

 Date: 23/10/2025 11:21:38
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for fx_theme
-- ----------------------------
DROP TABLE IF EXISTS `fx_theme`;
CREATE TABLE `fx_theme`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `year` int NOT NULL COMMENT '年份',
  `theme_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '法律主题月名称',
  `start_date` date NOT NULL COMMENT '开始时间',
  `end_date` date NOT NULL COMMENT '结束时间',
  `modifier` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'admin' COMMENT '修改人',
  `modify_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  `status` tinyint NULL DEFAULT 1 COMMENT '状态：0-废弃，1-使用',
  `generate` tinyint(1) UNSIGNED ZEROFILL NULL DEFAULT 0 COMMENT '状态：0-主题报告未生成，1-主题报告已生成',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 109 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '法律主题月表' ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
