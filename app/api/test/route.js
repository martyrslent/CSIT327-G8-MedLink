import clientPromise from "@/lib/mongodb";

export async function GET() {
    try {
        const client = await clientPromise;
        const db = client.db("mydb");
        const collections = await db.listCollections().toArray();

        return Response.json({ collections });
    } catch (e) {
        return Response.json({ error: e.message }, { status: 500 });
    }
}
