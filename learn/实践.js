(() => {
  'use strict';
  const tracks = {
    programmer: {
      title: '把熟悉的一项重复工作，做成能复核的小工具',
      task: '选一个你能判断对错的任务，例如从脱敏日志整理异常清单。先写清输入与期望输出，再让AI辅助实现；准备正常、边界与失败样例，不只看它能否运行。',
      outputs: ['一份问题说明与可授权的样本', '一个可运行的工具与使用说明', '正常、边界、失败结果的验收记录'],
      link: '/topics/fde-first-battle.html', label: '阅读：FDE的第一个项目'
    },
    student: {
      title: '用公开或自建资料，完成一次从问题到验收的小练习',
      task: '先选一个你能理解的任务，例如从公开活动通知整理日程。保留原始资料，写出期望结果，用一组新资料独立测试；不把AI给出的解释直接当作正确答案。',
      outputs: ['一份来源清楚、不含他人隐私的练习资料', '一项能独立复现的任务结果', '结果检查与修改前后的复盘'],
      link: '/topics/fde-what-is.html', label: '阅读：FDE到底在解决什么问题'
    },
    business: {
      title: '先把你熟悉的一项工作，说明白、拆清楚',
      task: '用自己的业务经验选择一个小任务，记录输入、输出、负责人、例外与人工判断。例如会议纪要转行动清单；先用脱敏或虚构样本练习，再判断哪些步骤适合AI。',
      outputs: ['一张现有做法、输入输出与负责人的流程说明', '一组AI辅助结果与人工复核对照', '哪些步骤有帮助、哪些必须由人决定的结论'],
      link: 'https://willeai.cn/services/consulting/', label: '了解：业务问题与AI应用条件的判断'
    }
  };
  document.querySelectorAll('input[name="track"]').forEach((input) => {
    input.addEventListener('change', () => {
      if (!input.checked || !Object.hasOwn(tracks, input.value)) return;
      const track = tracks[input.value];
      document.getElementById('track-title').textContent = track.title;
      document.getElementById('track-task').textContent = track.task;
      const outputs = document.getElementById('track-outputs');
      outputs.replaceChildren(...track.outputs.map((text) => {
        const item = document.createElement('li'); item.textContent = text; return item;
      }));
      const link = document.getElementById('track-article');
      link.href = track.link; link.textContent = track.label;
    });
  });
})();
