// Echte User Definition
const EXPERTS = ["Orion","Vega","Nova","Sirius","Polaris","OrionPrime","VegaX","NovaPro","SiriusGold","PolarisKing","TipJarAdmin","tipjarlogic","admin"];
const filterReal = { username: { $nin: EXPERTS }, email: { $exists:true, $ne:null } };

print("=== TIPJAR INSIGHTS - NUR ECHTE USER ===");
print("Echte registrierte User: " + db.users.countDocuments(filterReal));
print("Heute registriert: " + db.users.countDocuments({...filterReal, created_at: {$gte: new Date(new Date().setHours(0,0,0,0))}}));
print("Letzte 7 Tage: " + db.users.countDocuments({...filterReal, created_at: {$gte: new Date(Date.now()-7*24*60*60*1000)}}));

print("\n--- Views / Tips ---");
print("Total Tips: " + db.tips.countDocuments({}));
print("Tips von echten Usern: " + db.tips.countDocuments({username: {$nin: EXPERTS}}));
print("Total Views: " + db.tips.aggregate([{$group:{_id:null, sum:{$sum:"$views"}}}]).toArray()[0]?.sum || 0);

print("\n--- Engagement ---");
print("Active heute: " + db.users.countDocuments({...filterReal, last_login: {$gte: new Date(Date.now()-24*60*60*1000)}}));
