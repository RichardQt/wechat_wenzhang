/*
 Navicat Premium Dump SQL

 Source Server         : faxuan
 Source Server Type    : MySQL
 Source Server Version : 80043 (8.0.43)
 Source Host           : localhost:3306
 Source Schema         : faxuan

 Target Server Type    : MySQL
 Target Server Version : 80043 (8.0.43)
 File Encoding         : 65001

 Date: 25/09/2025 19:10:00
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for fx_education_articles
-- ----------------------------
DROP TABLE IF EXISTS `fx_education_articles`;
CREATE TABLE `fx_education_articles`  (
  `LLM_id` bigint(1) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `id` bigint(1) UNSIGNED ZEROFILL NOT NULL COMMENT '记录表的id',
  `article_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '文章ID',
  `unit_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '单位名称',
  `unit_property` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '单位属性（市级单位、区级单位等）',
  `industry_system` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '行业系统（法院系统、检察系统等）',
  `unit_district` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '单位所在区',
  `people_scale` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '人数规模（1-50人、51-100人等）',
  `month` char(7) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '月份（格式：YYYY-MM）',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `update_time` datetime NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  `type_class` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '是否为普法，0为非普法，1为普法',
  `modify_state` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '是否为人为修改，0为大模型判断，1为人为修改',
  `modifier` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '修改人',
  `modify_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`LLM_id`) USING BTREE,
  UNIQUE INDEX `idx_article_id`(`article_id` ASC) USING BTREE,
  INDEX `idx_unit_property`(`unit_property` ASC) USING BTREE,
  INDEX `idx_industry_system`(`industry_system` ASC) USING BTREE,
  INDEX `idx_month`(`month` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2000012181 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '普法教育文章信息表' ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
