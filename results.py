
import matplotlib.pyplot as plt

def main():
    ...
    flavors = ["single", "threaded", "multiprocess"]
    values = {
        "readonly": [340, 293, 278],
        "readwrite": [344, 297, 285],
    }

    with plt.xkcd():
        fig, ax = plt.subplots(layout='constrained')

        res = ax.grouped_bar(values, tick_labels=flavors, group_spacing=1)
        for container in res.bar_containers:
            ax.bar_label(container, padding=3)

        # Add some text for labels, title, etc.
        ax.set_ylabel('Time (ms)')
        ax.set_title('SQLite Benchmarks')
        ax.legend(loc='upper left', ncols=3)
        ax.set_ylim(0, 500)

        plt.savefig("results.png")
        plt.show()


if __name__ == "__main__":
    main()
