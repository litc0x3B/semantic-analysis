using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace YuGiOhDomain
{
    public enum EntityState
    {
        Unchanged,
        Added,
        Modified,
        Deleted
    }

    public abstract class BaseEntity
    {
        public EntityState State { get; set; } = EntityState.Unchanged;
    }

    public class Duelist : BaseEntity
    {
        public int Id { get; set; }
        public string Nickname { get; set; }
        
        public virtual List<DuelParticipation> Participations { get; set; } = new List<DuelParticipation>();
        public virtual List<Round> WonRounds { get; set; } = new List<Round>();

        public Duelist(string nickname)
        {
            Nickname = nickname;
        }
    }

    public class Duel : BaseEntity
    {
        public int Id { get; set; }
        public virtual List<DuelParticipation> Participations { get; set; } = new List<DuelParticipation>();
        public virtual List<Round> Rounds { get; set; } = new List<Round>();
    }

    public class DuelParticipation : BaseEntity
    {
        public int DuelId { get; set; }
        public virtual Duel Duel { get; set; }

        public int DuelistId { get; set; }
        public virtual Duelist Duelist { get; set; }

        public DuelParticipation(Duel duel, Duelist duelist)
        {
            Duel = duel ?? throw new ArgumentNullException(nameof(duel));
            Duelist = duelist ?? throw new ArgumentNullException(nameof(duelist));
            DuelId = duel.Id;
            DuelistId = duelist.Id;
        }
    }

    public class Round : BaseEntity
    {
        public int Id { get; set; }
        public int Number { get; set; }
        public int DuelId { get; set; }
        public virtual Duel Duel { get; set; }

        public int? WinnerId { get; set; }
        public virtual Duelist? Winner { get; set; }

        public Round(int number, Duel duel)
        {
            Number = number;
            Duel = duel ?? throw new ArgumentNullException(nameof(duel));
        }
    }

    public class SqlBatchGenerator
    {
        public string GenerateCommitScript(
            List<Duelist> duelists, 
            List<Duel> duels, 
            List<Round> rounds,
            List<DuelParticipation> participations)
        {
            var sb = new StringBuilder();
            sb.AppendLine("BEGIN TRANSACTION;");

            // Вставки
            foreach (var d in duelists.Where(x => x.State == EntityState.Added))
            {
                sb.AppendLine($"INSERT INTO Duelists (Id, Nickname) VALUES ({d.Id}, '{d.Nickname}');");
            }

            foreach (var duel in duels.Where(x => x.State == EntityState.Added))
            {
                sb.AppendLine($"INSERT INTO Duels (Id) VALUES ({duel.Id});");
            }

            foreach (var p in participations.Where(x => x.State == EntityState.Added))
            {
                sb.AppendLine($"INSERT INTO DuelParticipants (DuelId, DuelistId) VALUES ({p.DuelId}, {p.DuelistId});");
            }

            foreach (var r in rounds.Where(x => x.State == EntityState.Added))
            {
                int duelId = r.Duel?.Id ?? r.DuelId; 
                string winnerVal = r.WinnerId.HasValue ? r.WinnerId.Value.ToString() : "NULL";
                
                sb.AppendLine($"INSERT INTO Rounds (Number, DuelId, WinnerId) " +
                              $"VALUES ({r.Number}, {duelId}, {winnerVal});");
            }

            // Обновления
            foreach (var d in duelists.Where(x => x.State == EntityState.Modified))
            {
                sb.AppendLine($"UPDATE Duelists SET Nickname = '{d.Nickname}' WHERE Id = {d.Id};");
            }

            foreach (var r in rounds.Where(x => x.State == EntityState.Modified))
            {
                string winnerVal = r.WinnerId.HasValue ? r.WinnerId.Value.ToString() : "NULL";
                sb.AppendLine($"UPDATE Rounds SET WinnerId = {winnerVal} WHERE Id = {r.Id};");
            }
            
            // Удаления
            foreach (var r in rounds.Where(x => x.State == EntityState.Deleted))
            {
                sb.AppendLine($"DELETE FROM Rounds WHERE Id = {r.Id};");
            }
            
            foreach (var p in participations.Where(x => x.State == EntityState.Deleted))
            {
                sb.AppendLine($"DELETE FROM DuelParticipants WHERE DuelId = {p.DuelId} AND DuelistId = {p.DuelistId};");
            }

            foreach (var duel in duels.Where(x => x.State == EntityState.Deleted))
            {
                sb.AppendLine($"DELETE FROM Duels WHERE Id = {duel.Id};");
            }

            foreach (var d in duelists.Where(x => x.State == EntityState.Deleted))
            {
                sb.AppendLine($"DELETE FROM Duelists WHERE Id = {d.Id};");
            }

            sb.AppendLine("COMMIT;");
            return sb.ToString();
        }
    }
}