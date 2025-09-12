// Example: Access via
// http://localhost:3000/api/test-db

import mongoose from "mongoose";
import { connectDB } from "../../lib/mongodb";

export default async function handler(req, res) {
    try {
        await connectDB();

        const collections = await mongoose.connection.db.listCollections().toArray();
        const collectionNames = collections.map((col) => col.name);

        res.status(200).json({
            message: "✅ Database connection successful!",
            collections: collectionNames,
        });
    } catch (error) {
        console.error("DB Test Error:", error);
        res.status(500).json({ message: "❌ Database connection failed", error });
    }
}
