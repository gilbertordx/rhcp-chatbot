module.exports = (sequelize, DataTypes) => {
    const User = sequelize.define(
        'User',
        {
            id: {
                type: DataTypes.INTEGER,
                autoIncrement: true,
                primaryKey: true,
                allowNull: false,
            },
            name: {
                type: DataTypes.STRING,
                allowNull: false,
            },
            email: {
                type: DataTypes.STRING,
                allowNull: false,
            },
            password: {
                type: DataTypes.STRING,
                allowNull: false,
            },
            date_ofbirth: {
                type: DataTypes.DATE,
                allowNull: false,
            },
            last_activity: {
                type: DataTypes.DATE,
                allowNull: false,
                defaultValue: DataTypes.NOW,
            },
            created_at: {
                type: DataTypes.DATE,
                allowNull: false,
                defaultValue: DataTypes.NOW,
            },
            updated_at: {
                type: DataTypes.DATE,
                allowNull: false,
                defaultValue: DataTypes.NOW,
            },
            deleted_at: {
                type: DataTypes.DATE,
                allowNull: true,
            },
        },
        {
            sequelize, 
            tableName: 'users',
            modelName: 'User',
            underscored: true,
            timestamps: true,
            paranoid: true, 
            createdAt: 'created_at',
            updatedAt: 'updated_at',
            deletedAt: 'deleted_at',
        }
    );

    return User;
};