using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using FluentAssertions;
using NUnit.Framework;
using Projeny.Internal;

namespace Projeny.Test
{
    public class YamlWriterTest
    {
        [Test]
        public void TestReading()
        {
            var prj = PrjSerializer.DeserializeProjectConfig(text);
            var text2 = PrjSerializer.SerializeProjectConfig(prj);

            text2.Should().BeEquivalentTo(text);
        }

        const string text = @"AssetsFolder:
- GunShip
- TextMesh Pro
- AddressableAssetsData
ProjectSettingsPath: '[ProjectRoot]/ProjectSettings'
PluginsFolder:
- SteamVR
- UnityTools
- UnityTestTools
- UnityCompileFixes
- Force Field
- Realistic Explosions Pack
- Unique Projectiles Volume 1
- UnityAssetUsageDetector
- FluentAssertions
- NaughtyAttributes
- UnityStandardAssets-Environment
- ClassicSkybox
- WeaponSystem
TargetPlatforms:
- Windows
- UWP
";
    }


}
