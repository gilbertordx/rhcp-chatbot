/**
 * User Routes
 * 
 * This module defines all user-related endpoints.
 * It handles user registration, authentication, and profile management.
 */

const express = require('express');
const router = express.Router();
const userController = require('../controllers/user.controller');
const authMiddleware = require('../middleware/auth.middleware');

// Public routes
router.post('/register', userController.register);
router.post('/login', userController.login);

// Protected routes
router.get('/profile', authMiddleware.authenticate, userController.getProfile);
router.put('/profile', authMiddleware.authenticate, userController.updateProfile);
router.put('/password', authMiddleware.authenticate, userController.updatePassword);

// Admin routes
router.get('/', authMiddleware.authenticate, authMiddleware.isAdmin, userController.list);
router.get('/:id', authMiddleware.authenticate, authMiddleware.isAdmin, userController.getById);
router.put('/:id', authMiddleware.authenticate, authMiddleware.isAdmin, userController.update);
router.delete('/:id', authMiddleware.authenticate, authMiddleware.isAdmin, userController.delete);

module.exports = router; 