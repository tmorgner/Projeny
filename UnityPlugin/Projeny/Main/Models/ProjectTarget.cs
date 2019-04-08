using System.Globalization;

namespace Projeny
{
    public struct ProjectTarget
    {
        public string Target;
        public string Tag;

        public object ToArgument()
        {
            if (string.IsNullOrEmpty(Tag))
            {
                return Target.ToLower(CultureInfo.InvariantCulture);
            }

            return $"{Target.ToLower(CultureInfo.InvariantCulture)}-{Tag}";
        }
    }
}